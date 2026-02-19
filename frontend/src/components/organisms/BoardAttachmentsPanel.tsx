"use client";

import { useCallback, useRef, useState } from "react";
import {
  Download,
  FileText,
  Image as ImageIcon,
  Paperclip,
  Trash2,
  Upload,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { ApiError, uploadFetch } from "@/api/mutator";
import { customFetch } from "@/api/mutator";
import { cn } from "@/lib/utils";

export type BoardAttachment = {
  id: string;
  board_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  uploaded_by: string | null;
  description: string | null;
  download_url: string;
  created_at: string;
};

type BoardAttachmentsPanelProps = {
  boardId: string;
  attachments: BoardAttachment[];
  onClose: () => void;
  onRefresh: () => void;
  canWrite: boolean;
};

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatUploaderName(uploaded_by: string | null): string {
  if (!uploaded_by) return "Unknown";
  const parts = uploaded_by.split(":");
  return parts.length > 1 ? parts.slice(1).join(":") : uploaded_by;
}

function fileIcon(contentType: string) {
  if (contentType.startsWith("image/")) {
    return <ImageIcon className="h-4 w-4 text-indigo-500" />;
  }
  return <FileText className="h-4 w-4 text-slate-500" />;
}

function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function BoardAttachmentsPanel({
  boardId,
  attachments,
  onClose,
  onRefresh,
  canWrite,
}: BoardAttachmentsPanelProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [deleteInProgress, setDeleteInProgress] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      setUploadError(null);
      setIsUploading(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        await uploadFetch<BoardAttachment>(
          `/api/v1/boards/${boardId}/attachments`,
          formData,
        );
        onRefresh();
      } catch (err) {
        if (err instanceof ApiError) {
          setUploadError(err.message);
        } else {
          setUploadError("Upload failed.");
        }
      } finally {
        setIsUploading(false);
      }
    },
    [boardId, onRefresh],
  );

  const handleFileInput = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        handleUpload(file);
      }
      // Reset input so the same file can be re-selected
      e.target.value = "";
    },
    [handleUpload],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) {
        handleUpload(file);
      }
    },
    [handleUpload],
  );

  const handleDelete = useCallback(
    async (attachmentId: string) => {
      setDeleteInProgress(attachmentId);
      try {
        await customFetch(
          `/api/v1/boards/${boardId}/attachments/${attachmentId}`,
          { method: "DELETE" },
        );
        onRefresh();
      } catch {
        // Silently fail; the item will remain visible
      } finally {
        setDeleteInProgress(null);
      }
    },
    [boardId, onRefresh],
  );

  const handleDownload = useCallback((attachment: BoardAttachment) => {
    window.open(attachment.download_url, "_blank");
  }, []);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Attachments
          </p>
          <p className="mt-1 text-sm font-medium text-slate-900">
            {attachments.length === 0
              ? "No files attached"
              : `${attachments.length} file${attachments.length !== 1 ? "s" : ""}`}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-50"
          aria-label="Close attachments"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {/* Upload zone */}
        {canWrite ? (
          <div
            className={cn(
              "mb-4 rounded-xl border-2 border-dashed p-6 text-center transition",
              isDragOver
                ? "border-indigo-400 bg-indigo-50"
                : "border-slate-200 bg-slate-50 hover:border-slate-300",
              isUploading && "pointer-events-none opacity-60",
            )}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleDrop}
          >
            <Upload className="mx-auto h-6 w-6 text-slate-400" />
            <p className="mt-2 text-sm text-slate-600">
              {isUploading ? (
                "Uploading..."
              ) : (
                <>
                  Drag & drop a file or{" "}
                  <button
                    type="button"
                    className="font-semibold text-indigo-600 hover:text-indigo-700"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    browse
                  </button>
                </>
              )}
            </p>
            <p className="mt-1 text-xs text-slate-400">Max 25 MB per file</p>
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              onChange={handleFileInput}
            />
          </div>
        ) : null}

        {uploadError ? (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {uploadError}
          </div>
        ) : null}

        {/* Attachment list */}
        {attachments.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-400">
            <Paperclip className="h-8 w-8" />
            <p className="mt-3 text-sm">
              No files attached to this board yet.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {attachments.map((attachment) => (
              <div
                key={attachment.id}
                className="group flex items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2.5 transition hover:border-slate-300"
              >
                <div className="flex-shrink-0">
                  {fileIcon(attachment.content_type)}
                </div>
                <div className="min-w-0 flex-1">
                  <button
                    type="button"
                    onClick={() => handleDownload(attachment)}
                    className="block max-w-full truncate text-left text-sm font-medium text-slate-900 hover:text-indigo-600"
                    title={attachment.filename}
                  >
                    {attachment.filename}
                  </button>
                  <p className="text-xs text-slate-500">
                    {formatBytes(attachment.size_bytes)}
                    {" · "}
                    {formatUploaderName(attachment.uploaded_by)}
                    {" · "}
                    {formatTimestamp(attachment.created_at)}
                  </p>
                </div>
                <div className="flex flex-shrink-0 items-center gap-1 opacity-0 transition group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={() => handleDownload(attachment)}
                    className="rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                    title="Download"
                  >
                    <Download className="h-3.5 w-3.5" />
                  </button>
                  {canWrite ? (
                    <button
                      type="button"
                      onClick={() => handleDelete(attachment.id)}
                      disabled={deleteInProgress === attachment.id}
                      className="rounded p-1 text-slate-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                      title="Delete"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
