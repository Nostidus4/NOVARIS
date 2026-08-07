import { Eye } from "lucide-react";

export function ReadOnlyNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="readonly-note">
      <Eye size={13} />
      {children}
    </div>
  );
}
