'use client';

import { memo } from 'react';
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { cn } from '@/lib/utils';

// Color mapping for entity types
const entityColors: Record<string, string> = {
  person: 'bg-blue-500 border-blue-600',
  organization: 'bg-green-500 border-green-600',
  location: 'bg-orange-500 border-orange-600',
  date: 'bg-purple-500 border-purple-600',
  document: 'bg-gray-500 border-gray-600',
  topic: 'bg-pink-500 border-pink-600',
  event: 'bg-red-500 border-red-600',
  product: 'bg-yellow-500 border-yellow-600',
  financial_item: 'bg-emerald-500 border-emerald-600',
  default: 'bg-slate-500 border-slate-600',
};

type EntityNodeData = {
  name: string;
  type: string;
  description?: string;
};

type EntityNodeType = Node<EntityNodeData, 'entity'>;

function EntityNodeComponent({ data, selected }: NodeProps<EntityNodeType>) {
  const colorClass = entityColors[data.type?.toLowerCase()] || entityColors.default;

  return (
    <div
      className={cn(
        'px-3 py-2 rounded-lg border-2 shadow-md min-w-[120px] max-w-[200px] transition-all',
        colorClass,
        selected && 'ring-2 ring-white ring-offset-2 ring-offset-background'
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-white" />
      <div className="text-white text-center">
        <div className="text-xs font-medium opacity-80 uppercase tracking-wide">
          {data.type}
        </div>
        <div className="text-sm font-semibold truncate" title={data.name}>
          {data.name}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} className="!bg-white" />
    </div>
  );
}

export const EntityNode = memo(EntityNodeComponent);
