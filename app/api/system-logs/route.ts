import { NextResponse } from "next/server";
import { evaluateWithRocketRide } from "../../lib/rocketride";

export const dynamic = "force-dynamic";

type ButterbaseLogRow = {
  event?: string;
  timestamp?: string;
};

const invalidAppIds = new Set(["app_30r72zucnm70"]);

const demoEvents: ButterbaseLogRow[] = [
  {
    event: "[Boot] Vagus dashboard linked to local demo stream.",
    timestamp: new Date(Date.now() - 14000).toISOString(),
  },
  {
    event: "[Biometrics] Demo mode: dG/dt=0.0, HRV=55.0, compression_low=False.",
    timestamp: new Date(Date.now() - 11000).toISOString(),
  },
  {
    event: "[RocketRide] key-armed demo runtime selected gpt-5.5.",
    timestamp: new Date(Date.now() - 8000).toISOString(),
  },
  {
    event: "[Classifier] RocketRide evaluated energy as MEDIUM.",
    timestamp: new Date(Date.now() - 6500).toISOString(),
  },
  {
    event: "[Neo4j] Blocked candidate: Ship dashboard waits on Seed test graph.",
    timestamp: new Date(Date.now() - 5000).toISOString(),
  },
  {
    event: "[Daytona] Sandbox armed for low-energy crash branch.",
    timestamp: new Date(Date.now() - 2000).toISOString(),
  },
];

function normalizeRows(rows: ButterbaseLogRow[]) {
  return rows
    .filter((row) => row.event)
    .map((row, index) => ({
      id: `${row.timestamp ?? "demo"}-${index}`,
      event: row.event ?? "",
      timestamp: row.timestamp ?? new Date().toISOString(),
    }))
    .sort((a, b) => Date.parse(a.timestamp) - Date.parse(b.timestamp));
}

export async function GET() {
  const appId = process.env.BUTTERBASE_APP_ID?.trim();
  const token = process.env.BUTTERBASE_API_TOKEN?.trim();

  if (!appId || !token || invalidAppIds.has(appId)) {
    const rocketride = await evaluateWithRocketRide({
      glucoseChange: 0,
      hrv: 55,
      isCompressionLow: false,
    });
    return NextResponse.json({
      source: "demo",
      rows: normalizeRows([
        ...demoEvents,
        ...rocketride.events.map((event, index) => ({
          event,
          timestamp: new Date(Date.now() - 3500 + index * 750).toISOString(),
        })),
      ]),
    });
  }

  try {
    const response = await fetch(
      `https://api.butterbase.ai/v1/${appId}/system_logs`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      },
    );

    if (!response.ok) {
      return NextResponse.json(
        {
          source: "demo",
          rows: normalizeRows(demoEvents),
          error: `Butterbase returned ${response.status}`,
        },
        { status: 200 },
      );
    }

    const payload = await response.json();
    const rows = Array.isArray(payload) ? payload : payload.data ?? [];

    return NextResponse.json({
      source: "butterbase",
      rows: normalizeRows(rows).slice(-120),
    });
  } catch (error) {
    return NextResponse.json({
      source: "demo",
      rows: normalizeRows(demoEvents),
      error: error instanceof Error ? error.message : "Unknown log fetch error",
    });
  }
}
