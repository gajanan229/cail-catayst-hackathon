import type { ReactNode } from "react";
import {
  Check,
  AlertTriangle,
  LockKeyhole,
  ArrowUpRight,
  CircleHelp,
  RefreshCw,
} from "lucide-react";
import { useConsole } from "@/realtime/store";
import { Button } from "./ui/button";
import { cn } from "@/lib/utils";
export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: string;
  className?: string;
}) {
  return (
    <span className={cn("badge", `tone-${tone}`, className)}>{children}</span>
  );
}
export function Tier({ tier }: { tier: string }) {
  return (
    <Badge
      tone={
        tier === "T0"
          ? "ok"
          : tier === "T1"
            ? "warn"
            : tier === "T2"
              ? "crit"
              : "neutral"
      }
    >
      {tier === "T3" && <LockKeyhole size={10} />} {tier}
    </Badge>
  );
}
export function Panel({
  title,
  action,
  children,
  className,
  subtitle,
}: {
  title: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  subtitle?: string;
}) {
  return (
    <section className={cn("panel", className)}>
      <div className="panel-heading">
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
export function Empty({
  title,
  children,
  icon,
}: {
  title: string;
  children?: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="empty-state">
      {icon || <Check size={24} />}
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}
export function Loading() {
  return (
    <div className="skeletons" aria-label="Loading" role="status">
      <div />
      <div />
      <div />
    </div>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry: () => void;
}) {
  return (
    <div className="error-state">
      <AlertTriangle size={20} />
      <p>{message}</p>
      <Button onClick={retry}>
        <RefreshCw size={14} /> Retry
      </Button>
    </div>
  );
}
export function SourceLink({
  label,
  onClick,
}: {
  label: string;
  onClick: () => void;
}) {
  return (
    <button className="source-link" onClick={onClick}>
      {label}
      <ArrowUpRight size={11} />
    </button>
  );
}
export function Why({
  explanation,
  rules,
}: {
  explanation: string;
  rules?: string[];
}) {
  return (
    <details className="why">
      <summary>
        <CircleHelp size={12} /> Why?
      </summary>
      <p>{explanation}</p>
      {rules?.map((r) => (
        <code key={r}>{r}</code>
      ))}
    </details>
  );
}
export function ActorStamp() {
  const actor = useConsole((s) => s.actor);
  const users = useConsole((s) => s.users);
  const user = users.find((u) => u.id === actor);
  return (
    <span className="actor-stamp">
      <span className="avatar tiny">{user?.initials || "PR"}</span>
      {user?.name || "Priya"}
    </span>
  );
}
