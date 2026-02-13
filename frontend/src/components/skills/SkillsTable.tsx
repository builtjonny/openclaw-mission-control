import { useMemo, useState } from "react";

import {
  type ColumnDef,
  type OnChangeFn,
  type SortingState,
  type Updater,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";

import { type SkillRead } from "@/api/generated/model";
import {
  DataTable,
  type DataTableEmptyState,
} from "@/components/tables/DataTable";
import { dateCell } from "@/components/tables/cell-formatters";

type SkillsTableProps = {
  skills: SkillRead[];
  isLoading?: boolean;
  sorting?: SortingState;
  onSortingChange?: OnChangeFn<SortingState>;
  stickyHeader?: boolean;
  onEdit?: (skill: SkillRead) => void;
  onDelete?: (skill: SkillRead) => void;
  emptyState?: Omit<DataTableEmptyState, "icon"> & {
    icon?: DataTableEmptyState["icon"];
  };
};

const DEFAULT_EMPTY_ICON = (
  <svg
    className="h-16 w-16 text-slate-300"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 2L2 7l10 5 10-5-10-5z" />
    <path d="M2 17l10 5 10-5" />
    <path d="M2 12l10 5 10-5" />
  </svg>
);

const SOURCE_LABELS: Record<string, string> = {
  custom: "Custom",
  clawhub: "ClawHub",
};

export function SkillsTable({
  skills,
  isLoading = false,
  sorting,
  onSortingChange,
  stickyHeader = false,
  onEdit,
  onDelete,
  emptyState,
}: SkillsTableProps) {
  const [internalSorting, setInternalSorting] = useState<SortingState>([
    { id: "name", desc: false },
  ]);
  const resolvedSorting = sorting ?? internalSorting;
  const handleSortingChange: OnChangeFn<SortingState> =
    onSortingChange ??
    ((updater: Updater<SortingState>) => {
      setInternalSorting(updater);
    });

  const columns = useMemo<ColumnDef<SkillRead>[]>(
    () => [
      {
        accessorKey: "name",
        header: "Skill",
        cell: ({ row }) => (
          <div className="space-y-1">
            <p className="text-sm font-semibold text-slate-800">
              {row.original.name}
            </p>
            <p className="text-xs text-slate-500">
              {row.original.slug}
              {row.original.summary ? ` · ${row.original.summary}` : ""}
            </p>
          </div>
        ),
      },
      {
        accessorKey: "source",
        header: "Source",
        cell: ({ row }) => {
          const label =
            SOURCE_LABELS[row.original.source] ?? row.original.source;
          return (
            <span className="inline-flex items-center rounded-full border border-slate-200 bg-white px-2.5 py-0.5 text-xs font-medium text-slate-700">
              {label}
            </span>
          );
        },
      },
      {
        accessorKey: "category",
        header: "Category",
        cell: ({ row }) => (
          <span className="text-sm text-slate-600">
            {row.original.category ?? "-"}
          </span>
        ),
      },
      {
        accessorKey: "agent_count",
        header: "Agents",
        cell: ({ row }) => (
          <span className="text-sm font-medium text-slate-700">
            {row.original.agent_count ?? 0}
          </span>
        ),
      },
      {
        accessorKey: "updated_at",
        header: "Updated",
        cell: ({ row }) => dateCell(row.original.updated_at),
      },
    ],
    [],
  );

  // eslint-disable-next-line react-hooks/incompatible-library
  const table = useReactTable({
    data: skills,
    columns,
    state: {
      sorting: resolvedSorting,
    },
    onSortingChange: handleSortingChange,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <DataTable
      table={table}
      isLoading={isLoading}
      stickyHeader={stickyHeader}
      rowClassName="transition hover:bg-slate-50"
      cellClassName="px-6 py-4 align-top"
      rowActions={
        onEdit || onDelete
          ? {
              actions: [
                ...(onEdit
                  ? [{ key: "edit", label: "Edit", onClick: onEdit }]
                  : []),
                ...(onDelete
                  ? [{ key: "delete", label: "Delete", onClick: onDelete }]
                  : []),
              ],
            }
          : undefined
      }
      emptyState={
        emptyState
          ? {
              icon: emptyState.icon ?? DEFAULT_EMPTY_ICON,
              title: emptyState.title,
              description: emptyState.description,
              actionHref: emptyState.actionHref,
              actionLabel: emptyState.actionLabel,
            }
          : undefined
      }
    />
  );
}
