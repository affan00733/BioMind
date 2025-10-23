import { ButtonHTMLAttributes } from "react";
import clsx from "classnames";

type Variant = "default" | "primary" | "subtle";

export default function Button({ className, "data-variant": variant = "default", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { "data-variant"?: Variant }) {
  return (
    <button
      {...props}
      className={clsx(
        "inline-flex items-center gap-2 px-3 py-2 rounded-xl border text-text transition-colors focus:outline-none focus:ring-2",
        "focus:ring-[var(--focus)]",
        variant === "primary" && "border-transparent text-white bg-[linear-gradient(135deg,var(--accent)_0%,#34A853_50%,#13B0EA_100%)] hover:brightness-110",
  variant === "subtle" && "bg-transparent border-transparent hover:bg-[rgba(255,255,255,0.06)]",
  variant === "default" && "bg-[var(--surface)] text-[var(--text)] border-border hover:bg-[rgba(255,255,255,0.06)]",
        className
      )}
    />
  );
}
