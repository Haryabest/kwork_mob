'use client';

import { Badge, Text } from '@mantine/core';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { FixedSizeGrid as Grid } from 'react-window';

type ModelCard = {
  uuid: string;
  order_id: number;
  display_name?: string | null;
  publish_status?: string;
  order_status?: string | null;
  created_at?: string;
};

type Props = {
  items: ModelCard[];
  publishBadgeColor: (status?: string | null, orderStatus?: string | null) => string;
  publishLabel: (status?: string | null, orderStatus?: string | null) => string;
  virtualized?: boolean;
};

const CARD_W = 220;
const CARD_H = 268;
const GAP = 16;

function ModelCardTile({
  model,
  publishBadgeColor,
  publishLabel,
}: {
  model: ModelCard;
  publishBadgeColor: Props['publishBadgeColor'];
  publishLabel: Props['publishLabel'];
}) {
  const [thumb, setThumb] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { api } = await import('../services/api');
        const { data } = await api.get<{ thumbnail_url?: string }>(`/models/${model.uuid}/thumbnail`);
        if (!cancelled) setThumb(data.thumbnail_url || null);
      } catch {
        if (!cancelled) setThumb(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [model.uuid]);

  return (
    <Link
      href={`/models/${model.uuid}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: CARD_H,
        padding: GAP / 2,
        textDecoration: 'none',
        color: 'inherit',
      }}
    >
      <div
        style={{
          flex: 1,
          borderRadius: 12,
          overflow: 'hidden',
          background: 'rgba(0,87,184,0.06)',
          border: '1px solid rgba(0,87,184,0.08)',
          marginBottom: 8,
        }}
      >
        {thumb ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={thumb}
            alt=""
            loading="lazy"
            style={{ width: '100%', height: '100%', objectFit: 'cover' }}
          />
        ) : (
          <div style={{ width: '100%', height: '100%', minHeight: 140 }} />
        )}
      </div>
      <Text fw={600} size="sm" lineClamp={1}>
        {model.display_name || `${model.uuid.slice(0, 8)}…`}
      </Text>
      <Text size="xs" c="#6d6c77">
        #{model.order_id}
        {model.created_at ? ` · ${new Date(model.created_at).toLocaleDateString('ru-RU')}` : ''}
      </Text>
      <Badge
        variant="light"
        color={publishBadgeColor(model.publish_status, model.order_status)}
        size="sm"
        mt={4}
        w="fit-content"
      >
        {publishLabel(model.publish_status, model.order_status)}
      </Badge>
    </Link>
  );
}

export function ModelsGridView({ items, publishBadgeColor, publishLabel, virtualized }: Props) {
  const [width, setWidth] = useState(960);
  useEffect(() => {
    const el = document.getElementById('models-grid-host');
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width;
      if (w) setWidth(w);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const columnCount = Math.max(1, Math.floor((width + GAP) / (CARD_W + GAP)));
  const rowCount = Math.ceil(items.length / columnCount);
  const gridHeight = Math.min(720, rowCount * (CARD_H + GAP) + GAP);

  const cell = useMemo(
    () =>
      function Cell({
        columnIndex,
        rowIndex,
        style,
      }: {
        columnIndex: number;
        rowIndex: number;
        style: React.CSSProperties;
      }) {
        const idx = rowIndex * columnCount + columnIndex;
        if (idx >= items.length) return null;
        const model = items[idx];
        return (
          <div style={style}>
            <ModelCardTile
              model={model}
              publishBadgeColor={publishBadgeColor}
              publishLabel={publishLabel}
            />
          </div>
        );
      },
    [columnCount, items, publishBadgeColor, publishLabel],
  );

  if (!virtualized) {
    return (
      <div
        id="models-grid-host"
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(auto-fill, minmax(${CARD_W}px, 1fr))`,
          gap: GAP,
        }}
      >
        {items.map((m) => (
          <ModelCardTile
            key={m.uuid}
            model={m}
            publishBadgeColor={publishBadgeColor}
            publishLabel={publishLabel}
          />
        ))}
      </div>
    );
  }

  return (
    <div id="models-grid-host">
      <Grid
        columnCount={columnCount}
        columnWidth={CARD_W + GAP}
        height={gridHeight}
        rowCount={rowCount}
        rowHeight={CARD_H + GAP}
        width={columnCount * (CARD_W + GAP)}
      >
        {cell}
      </Grid>
    </div>
  );
}
