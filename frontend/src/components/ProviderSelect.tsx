import { useProviders } from "../hooks/useProviders";

const LABELS: Record<string, string> = { openai: "ChatGPT", claude: "Claude" };

type Props = { value: string; onChange: (value: string) => void };

export default function ProviderSelect({ value, onChange }: Props) {
  const providers = useProviders();
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-md border bg-white px-2 py-1.5 text-sm"
      aria-label="Model"
    >
      <option value="">Default model</option>
      {providers.map((p) => (
        <option key={p.name} value={p.name} disabled={!p.configured}>
          {LABELS[p.name] ?? p.name} · {p.model}
          {p.configured ? "" : " (no key)"}
        </option>
      ))}
    </select>
  );
}
