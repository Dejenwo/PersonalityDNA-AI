"use client";

import { useEffect } from "react";
import { type ProductEvent, track } from "@/lib/analytics";
import { captureAttribution } from "@/lib/attribution";

function localStore() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

/** Keeps first-touch referral and campaign tags from the landing link (sent once at sign-up). */
export function AttributionCapture() {
  useEffect(() => {
    const found = captureAttribution(window.location.search, localStore());
    if (found?.referral) track("referral_landing");
  }, []);
  return null;
}

/** Counts one anonymous view of a page. */
export function TrackView({ event }: { event: ProductEvent }) {
  useEffect(() => track(event), [event]);
  return null;
}
