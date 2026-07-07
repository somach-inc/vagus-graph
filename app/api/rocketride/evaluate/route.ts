import { NextResponse } from "next/server";
import { evaluateWithRocketRide } from "../../../lib/rocketride";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));

  const result = await evaluateWithRocketRide({
    glucoseChange: Number(body.glucoseChange ?? body.glucose_change ?? 0),
    hrv: Number(body.hrv ?? 55),
    isCompressionLow: Boolean(
      body.isCompressionLow ?? body.is_compression_low ?? false,
    ),
  });

  return NextResponse.json(result);
}
