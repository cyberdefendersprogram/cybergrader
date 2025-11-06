import DOMPurify from "dompurify";
import { marked } from "marked";
import type { NoteDocument } from "../types";

interface NotesSectionProps {
  note: NoteDocument | null;
}

export function NotesSection({ note }: NotesSectionProps) {
  if (!note) {
    return null;
  }

  const html = marked.parse(note.body, { async: false }) as string;
  const sanitized = DOMPurify.sanitize(html);

  return (
    <section className="card">
      <h2>Lecture notes</h2>
      <div className="markdown">
        <h3 style={{ marginTop: 0 }}>{note.name.replace(/[-_]/g, " ")}</h3>
        <div dangerouslySetInnerHTML={{ __html: sanitized }} />
      </div>
    </section>
  );
}
