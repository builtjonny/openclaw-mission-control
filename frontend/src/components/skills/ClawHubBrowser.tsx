"use client";

import { useCallback, useState } from "react";

import { ApiError } from "@/api/mutator";
import {
  useImportClawhubSkillApiV1SkillsClawhubImportPost,
  useSearchClawhubApiV1SkillsClawhubSearchGet,
  type searchClawhubApiV1SkillsClawhubSearchGetResponse,
} from "@/api/generated/skills/skills";
import type { ClawHubSearchResult } from "@/api/generated/model";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type ClawHubBrowserProps = {
  onImported?: () => void;
};

const extractErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof ApiError) return error.message || fallback;
  if (error instanceof Error) return error.message || fallback;
  return fallback;
};

export function ClawHubBrowser({ onImported }: ClawHubBrowserProps) {
  const [query, setQuery] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [importingSlug, setImportingSlug] = useState<string | null>(null);
  const [importedSlugs, setImportedSlugs] = useState<Set<string>>(new Set());
  const [importError, setImportError] = useState<string | null>(null);

  const searchQuery =
    useSearchClawhubApiV1SkillsClawhubSearchGet<
      searchClawhubApiV1SkillsClawhubSearchGetResponse,
      ApiError
    >(
      { q: searchTerm, limit: 20 },
      {
        query: {
          enabled: Boolean(searchTerm),
          retry: false,
        },
      },
    );

  const importMutation =
    useImportClawhubSkillApiV1SkillsClawhubImportPost<ApiError>({
      mutation: {
        retry: false,
      },
    });

  const results: ClawHubSearchResult[] =
    searchQuery.data?.status === 200
      ? (searchQuery.data.data as ClawHubSearchResult[])
      : [];

  const handleSearch = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      const trimmed = query.trim();
      if (trimmed) setSearchTerm(trimmed);
    },
    [query],
  );

  const handleImport = useCallback(
    async (slug: string) => {
      setImportingSlug(slug);
      setImportError(null);
      try {
        const result = await importMutation.mutateAsync({
          data: { clawhub_slug: slug },
        });
        if (result.status === 200) {
          setImportedSlugs((prev) => new Set(prev).add(slug));
          onImported?.();
        } else {
          setImportError("Unable to import skill.");
        }
      } catch (error) {
        setImportError(extractErrorMessage(error, "Unable to import skill."));
      } finally {
        setImportingSlug(null);
      }
    },
    [importMutation, onImported],
  );

  return (
    <div className="space-y-6">
      <form onSubmit={handleSearch} className="flex gap-3">
        <Input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search ClawHub skills..."
          className="flex-1"
        />
        <Button type="submit" disabled={!query.trim() || searchQuery.isLoading}>
          {searchQuery.isLoading ? "Searching..." : "Search"}
        </Button>
      </form>

      {importError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          {importError}
        </div>
      ) : null}

      {searchQuery.error ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
          {searchQuery.error.message}
        </div>
      ) : null}

      {searchTerm && !searchQuery.isLoading && results.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center">
          <p className="text-sm text-slate-500">
            No skills found for &ldquo;{searchTerm}&rdquo;
          </p>
        </div>
      ) : null}

      {results.length > 0 ? (
        <div className="space-y-3">
          {results.map((result) => {
            const slug = result.slug ?? "";
            const alreadyImported = importedSlugs.has(slug);
            const isImporting = importingSlug === slug;

            return (
              <div
                key={slug}
                className="flex items-start justify-between gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300"
              >
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="text-sm font-semibold text-slate-800">
                    {result.display_name ?? slug}
                  </p>
                  <p className="text-xs text-slate-500">
                    {slug}
                    {result.version ? ` · v${result.version}` : ""}
                  </p>
                  {result.summary ? (
                    <p className="text-sm text-slate-600">{result.summary}</p>
                  ) : null}
                </div>
                <div className="shrink-0">
                  {alreadyImported ? (
                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                      Added
                    </span>
                  ) : (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleImport(slug)}
                      disabled={isImporting}
                    >
                      {isImporting ? "Adding..." : "Add to directory"}
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
