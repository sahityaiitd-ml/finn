import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "FINN",
    short_name: "FINN",
    description: "Evidence, not verdicts.",
    start_url: "/",
    display: "standalone",
    background_color: "#f4efe8",
    theme_color: "#f4efe8",
    icons: [{ src: "/icons/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" }],
  };
}
