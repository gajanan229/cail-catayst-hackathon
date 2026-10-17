import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
export const time = (ts?: string | null) =>
  ts
    ? new Date(ts).toLocaleTimeString("en-GB", {
        timeZone: "UTC",
        hour12: false,
      })
    : "—";
export const human = (s: string) => s.replaceAll("_", " ");
