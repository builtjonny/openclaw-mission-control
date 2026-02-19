"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError, customFetch } from "@/api/mutator";
import type { AgentRead } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

type AgentFileEditorDialogProps = {
  agent: AgentRead | null;
  fileName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved?: () => void;
};

const FILE_DESCRIPTIONS: Record<string, string> = {
  "SOUL.md": "Stable core identity. Persists across reprovisions.",
  "SELF.md": "Evolving preferences and personality. Agent-editable.",
  "TASK_SOUL.md": "Active task lens and context. Agent-editable.",
};

export function AgentFileEditorDialog({
  agent,
  fileName,
  open,
  onOpenChange,
  onSaved,
}: AgentFileEditorDialogProps) {
  const [content, setContent] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchContent = useCallback(async () => {
    if (!agent) return;
    setIsLoading(true);
    setError(null);
    try {
      const result = await customFetch<{ data: string; status: number }>(
        `/api/v1/agents/${agent.id}/files/${encodeURIComponent(fileName)}`,
        { method: "GET" },
      );
      setContent(typeof result.data === "string" ? result.data : "");
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to load file.";
      setError(message);
      setContent("");
    } finally {
      setIsLoading(false);
    }
  }, [agent, fileName]);

  useEffect(() => {
    if (open && agent) {
      fetchContent();
    }
  }, [open, agent, fetchContent]);

  const handleSave = async () => {
    if (!agent) return;
    setIsSaving(true);
    setError(null);
    try {
      await customFetch(
        `/api/v1/agents/${agent.id}/files/${encodeURIComponent(fileName)}`,
        {
          method: "PUT",
          body: JSON.stringify({ content: content.trim() }),
        },
      );
      onOpenChange(false);
      onSaved?.();
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to save file.";
      setError(message);
    } finally {
      setIsSaving(false);
    }
  };

  const busy = isLoading || isSaving;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        aria-label={`Edit ${fileName} for ${agent?.name ?? "agent"}`}
        className="max-w-3xl"
      >
        <DialogHeader>
          <DialogTitle>
            {agent?.name ?? "Agent"} &mdash; {fileName}
          </DialogTitle>
          <DialogDescription>
            {FILE_DESCRIPTIONS[fileName] ?? "Agent workspace file."}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex min-h-[200px] items-center justify-center text-sm text-slate-500">
            Loading {fileName}&hellip;
          </div>
        ) : (
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={18}
            className="mt-2 font-mono text-sm"
            disabled={busy}
          />
        )}

        {error ? (
          <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm text-slate-600 shadow-sm">
            {error}
          </div>
        ) : null}

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={busy || isLoading}>
            {isSaving ? "Saving\u2026" : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
