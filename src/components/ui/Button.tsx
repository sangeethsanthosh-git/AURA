import { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "quiet" | "ghost";
  children: ReactNode;
};

export function Button({ variant = "quiet", children, ...props }: ButtonProps) {
  return (
    <button className="button" data-variant={variant} {...props}>
      {children}
    </button>
  );
}
