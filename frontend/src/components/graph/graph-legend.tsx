'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const entityTypes = [
  { type: 'person', color: 'bg-blue-500', label: 'Person' },
  { type: 'organization', color: 'bg-green-500', label: 'Organization' },
  { type: 'location', color: 'bg-orange-500', label: 'Location' },
  { type: 'date', color: 'bg-purple-500', label: 'Date' },
  { type: 'document', color: 'bg-gray-500', label: 'Document' },
  { type: 'topic', color: 'bg-pink-500', label: 'Topic' },
  { type: 'event', color: 'bg-red-500', label: 'Event' },
  { type: 'product', color: 'bg-yellow-500', label: 'Product' },
  { type: 'financial_item', color: 'bg-emerald-500', label: 'Financial' },
];

export function GraphLegend() {
  return (
    <Card className="absolute bottom-4 left-4 z-10 w-48">
      <CardHeader className="py-2 px-3">
        <CardTitle className="text-sm">Entity Types</CardTitle>
      </CardHeader>
      <CardContent className="py-2 px-3">
        <div className="grid grid-cols-2 gap-1">
          {entityTypes.map(({ type, color, label }) => (
            <div key={type} className="flex items-center gap-1.5">
              <div className={`w-3 h-3 rounded ${color}`} />
              <span className="text-xs text-muted-foreground">{label}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
