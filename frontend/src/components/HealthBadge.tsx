import { useEffect, useState } from "react";
import { getHealth, type Health } from "../api/client";

export default function HealthBadge() {
  const [health, setHealth] = useState<Health | null>(null);
  const [down, setDown] = useState(false);

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setDown(true));
  }, []);

  if (down) return <span className="text-xs text-red-600">● API offline</span>;
  if (!health) return <span className="text-xs text-slate-400">● checking…</span>;
  return <span className="text-xs text-green-700">● API ok · {health.llm_provider}</span>;
}
