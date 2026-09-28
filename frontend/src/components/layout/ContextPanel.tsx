"use client";
import { useRef, useState, type ReactNode } from "react";
import { SlidersHorizontal, X } from "lucide-react";
export function ContextPanel({ children }: { children: ReactNode }) {
  const drawer = useRef<HTMLDialogElement>(null);
  const [open, setOpen] = useState(false);
  return (
    <>
      <aside className="context-panel">{!open && children}</aside>
      <button
        className="drawer-toggle"
        onClick={() => {
          setOpen(true);
          drawer.current?.showModal();
        }}
        aria-label="Open contextual panel"
      >
        <SlidersHorizontal size={17} /> Workspace controls
      </button>
      <dialog
        ref={drawer}
        onClose={() => setOpen(false)}
        className="context-drawer"
        aria-label="Contextual controls"
      >
        <button
          className="drawer-close"
          onClick={() => drawer.current?.close()}
          aria-label="Close contextual panel"
        >
          <X size={18} />
        </button>
        {open && children}
        <button onClick={() => drawer.current?.close()}>Return to globe</button>
      </dialog>
    </>
  );
}
