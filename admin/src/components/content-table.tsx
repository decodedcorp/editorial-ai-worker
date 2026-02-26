"use client";

import { useRouter } from "next/navigation";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { ArrowUpDown } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { ContentStatusBadge } from "@/components/content-status-badge";
import { PipelineStatusIndicator } from "@/components/pipeline-status-indicator";
import { formatDate } from "@/lib/utils";
import type { ContentItemWithSummary } from "@/lib/types";

const STATUS_TABS = [
  { value: "all", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
] as const;

const columns: ColumnDef<ContentItemWithSummary>[] = [
  {
    accessorKey: "title",
    header: ({ column }) => (
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Title
        <ArrowUpDown className="ml-1 size-3" />
      </Button>
    ),
    cell: ({ row }) => {
      const title = row.getValue<string>("title");
      return (
        <span className="font-medium">
          {title.length > 60 ? `${title.slice(0, 60)}...` : title}
        </span>
      );
    },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => <ContentStatusBadge status={row.getValue<string>("status")} />,
    enableSorting: false,
  },
  {
    id: "pipeline",
    header: "Pipeline",
    cell: ({ row }) => (
      <PipelineStatusIndicator
        status={row.original.status}
        pipelineSummary={row.original.pipeline_summary}
      />
    ),
    enableSorting: false,
  },
  {
    accessorKey: "keyword",
    header: "Keyword",
    cell: ({ row }) => (
      <span className="text-muted-foreground">{row.getValue<string>("keyword")}</span>
    ),
  },
  {
    accessorKey: "created_at",
    header: ({ column }) => (
      <Button
        variant="ghost"
        size="sm"
        className="-ml-3"
        onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
      >
        Created
        <ArrowUpDown className="ml-1 size-3" />
      </Button>
    ),
    cell: ({ row }) => formatDate(row.getValue<string>("created_at")),
  },
];

interface ContentTableProps {
  items: ContentItemWithSummary[];
  total: number;
  page: number;
  limit: number;
  currentStatus?: string;
}

export function ContentTable({
  items,
  total,
  page,
  limit,
  currentStatus,
}: ContentTableProps) {
  const router = useRouter();
  const [sorting, setSorting] = useState<SortingState>([
    { id: "created_at", desc: true },
  ]);

  const table = useReactTable({
    data: items,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    state: { sorting },
  });

  const activeTab = currentStatus || "all";
  const totalPages = Math.max(1, Math.ceil(total / limit));
  const start = (page - 1) * limit + 1;
  const end = Math.min(page * limit, total);

  function buildUrl(status?: string, p: number = 1) {
    const params = new URLSearchParams();
    if (status && status !== "all") params.set("status", status);
    if (p > 1) params.set("page", String(p));
    const qs = params.toString();
    return `/contents${qs ? `?${qs}` : ""}`;
  }

  return (
    <div className="space-y-4">
      {/* Tab filters */}
      <Tabs
        value={activeTab}
        onValueChange={(value) => router.push(buildUrl(value))}
      >
        <TabsList>
          {STATUS_TABS.map((tab) => (
            <TabsTrigger key={tab.value} value={tab.value}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* Data table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/contents/${row.original.id}`)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={columns.length} className="h-24 text-center">
                  No content found.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {total > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Showing {start}-{end} of {total}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => router.push(buildUrl(currentStatus, page - 1))}
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => router.push(buildUrl(currentStatus, page + 1))}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
