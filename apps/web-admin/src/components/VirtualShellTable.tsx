import { Text } from '@mantine/core';
import type { CSSProperties, ReactNode } from 'react';
import { FixedSizeList as VirtualList } from 'react-window';
import { ShellTable } from './Panel';

const VIRTUAL_MIN_ROWS = 80;
const VIRTUAL_ROW_HEIGHT = 48;
const VIRTUAL_MAX_HEIGHT = 640;

export function VirtualShellTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: ReactNode[][];
}) {
  if (rows.length < VIRTUAL_MIN_ROWS) {
    return <ShellTable headers={headers} rows={rows} />;
  }

  const colCount = headers.length;
  const gridTemplate = `repeat(${colCount}, minmax(120px, 1fr))`;
  const listHeight = Math.min(VIRTUAL_MAX_HEIGHT, rows.length * VIRTUAL_ROW_HEIGHT);
  const rowStyle: CSSProperties = {
    display: 'grid',
    gridTemplateColumns: gridTemplate,
    gap: 12,
    alignItems: 'center',
    padding: '0 16px',
    borderBottom: '1px solid var(--mantine-color-gray-2)',
    fontSize: 14,
  };

  return (
    <div className="vz-surface" style={{ padding: 0, overflowX: 'auto' }}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: gridTemplate,
          gap: 12,
          padding: '12px 16px',
          fontWeight: 600,
          fontSize: 13,
          borderBottom: '1px solid var(--mantine-color-gray-3)',
          minWidth: colCount * 120,
        }}
      >
        {headers.map((header) => (
          <Text key={header} size="sm" fw={600}>
            {header}
          </Text>
        ))}
      </div>
      <VirtualList
        height={listHeight}
        width="100%"
        itemCount={rows.length}
        itemSize={VIRTUAL_ROW_HEIGHT}
        style={{ minWidth: colCount * 120 }}
      >
        {({ index, style }) => (
          <div
            style={{
              ...style,
              ...rowStyle,
              background: index % 2 ? 'var(--mantine-color-gray-0)' : undefined,
            }}
          >
            {rows[index].map((cell, cellIndex) => (
              <div key={cellIndex}>{cell}</div>
            ))}
          </div>
        )}
      </VirtualList>
    </div>
  );
}
