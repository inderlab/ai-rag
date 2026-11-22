import { useEffect, useState } from "react";
import { getProviders, type Provider } from "../api/client";

export function useProviders() {
  const [providers, setProviders] = useState<Provider[]>([]);
  useEffect(() => {
    getProviders().then(setProviders).catch(() => setProviders([]));
  }, []);
  return providers;
}
