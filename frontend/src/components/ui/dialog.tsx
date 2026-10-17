import type { ReactNode } from 'react';
import { Dialog as Primitive } from 'radix-ui';
import { X } from 'lucide-react';
import { Button } from './button';
export function Dialog({open, onOpenChange, title, description, children, drawer = false}: {
  open: boolean; onOpenChange: (open: boolean) => void; title: string; description?: string; children: ReactNode; drawer?: boolean;
}) {
  return <Primitive.Root open={open} onOpenChange={onOpenChange}><Primitive.Portal>
    <Primitive.Overlay className="dialog-overlay" />
    <Primitive.Content className={drawer ? 'dialog-content drawer' : 'dialog-content'} aria-describedby={description ? undefined : undefined}>
      <div className="dialog-heading"><div><Primitive.Title>{title}</Primitive.Title>
      <Primitive.Description className={description ? 'muted' : 'sr-only'}>{description || title}</Primitive.Description></div>
      <Primitive.Close asChild><Button size="icon" variant="ghost" aria-label="Close"><X size={18}/></Button></Primitive.Close></div>
      {children}
    </Primitive.Content>
  </Primitive.Portal></Primitive.Root>;
}
