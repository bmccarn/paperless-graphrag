'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useGraphStore } from '@/lib/stores';
import { ChevronDown, ChevronUp, Palette } from 'lucide-react';

// Entity type categories matching the vibrant colors in graph-container.tsx
const entityCategories = [
  { category: 'People', colorHex: '#4A90E2', types: ['person', 'officer', 'shareholder'] },
  { category: 'Organizations', colorHex: '#2ECC71', types: ['organization'] },
  { category: 'Tax', colorHex: '#E67E22', types: ['tax preparer', 'tax form', 'tax schedule', 'tax identification number', 'shareholder record'] },
  { category: 'Financial', colorHex: '#1ABC9C', types: ['financial account', 'billing statement', 'transaction', 'monetary amount'] },
  { category: 'Training', colorHex: '#9B59B6', types: ['certification', 'training course', 'technical manual', 'hardware component'] },
  { category: 'Insurance', colorHex: '#E74C8C', types: ['insurance policy', 'insurance endorsement', 'insurance claim', 'policy provision'] },
  { category: 'Healthcare', colorHex: '#E74C3C', types: ['medical benefit', 'healthcare service'] },
  { category: 'Legal/Govt', colorHex: '#F1C40F', types: ['government benefits program', 'legal election/consent', 'statute or regulation'] },
  { category: 'Other', colorHex: '#7F8C9A', types: ['appraisal', 'address', 'date/event', 'electronic signature or pin'] },
];

export function GraphLegend() {
  const { colorBy } = useGraphStore();
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <>
      {/* Desktop Legend - Always visible */}
      <Card className="absolute bottom-4 right-4 z-10 w-52 hidden md:block bg-background/90 backdrop-blur-sm border-border/50">
        <CardHeader className="py-2 px-3">
          <CardTitle className="text-sm">
            {colorBy === 'type' ? 'Entity Categories' : 'Community Colors'}
          </CardTitle>
        </CardHeader>
        <CardContent className="py-2 px-3">
          {colorBy === 'type' ? (
            <div className="grid grid-cols-2 gap-1">
              {entityCategories.map(({ category, colorHex }) => (
                <div key={category} className="flex items-center gap-1.5">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: colorHex }}
                  />
                  <span className="text-xs text-muted-foreground">{category}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              Nodes are colored by community. Each unique community gets a distinct hue.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Mobile Legend - Collapsible */}
      <div className="absolute top-2 right-2 z-10 md:hidden">
        {isExpanded ? (
          <Card className="w-44 bg-background/90 backdrop-blur-sm border-border/50">
            <CardHeader className="py-1.5 px-2 flex flex-row items-center justify-between">
              <CardTitle className="text-xs">
                {colorBy === 'type' ? 'Categories' : 'Colors'}
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0"
                onClick={() => setIsExpanded(false)}
              >
                <ChevronUp className="h-3 w-3" />
              </Button>
            </CardHeader>
            <CardContent className="py-1.5 px-2">
              {colorBy === 'type' ? (
                <div className="grid grid-cols-2 gap-0.5">
                  {entityCategories.map(({ category, colorHex }) => (
                    <div key={category} className="flex items-center gap-1">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: colorHex }}
                      />
                      <span className="text-[10px] text-muted-foreground">{category}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[10px] text-muted-foreground">
                  Each community has a unique color.
                </p>
              )}
            </CardContent>
          </Card>
        ) : (
          <Button
            variant="outline"
            size="sm"
            className="h-8 w-8 p-0 bg-background/90 backdrop-blur-sm"
            onClick={() => setIsExpanded(true)}
          >
            <Palette className="h-4 w-4" />
          </Button>
        )}
      </div>
    </>
  );
}
