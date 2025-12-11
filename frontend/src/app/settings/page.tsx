'use client';

import { useState, useEffect } from 'react';
import {
  Settings as SettingsIcon,
  Save,
  RefreshCw,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { getSettings, updateSettings, testConnections } from '@/lib/api';
import { toast } from 'sonner';
import type { SettingsResponse, SettingValue, ConnectionTestResult } from '@/types';

// Group settings by category
const SETTING_GROUPS = {
  connections: {
    title: 'Connection Settings',
    description: 'Configure connections to Paperless-ngx and LiteLLM',
    keys: ['paperless_url', 'paperless_token', 'litellm_base_url', 'litellm_api_key'],
  },
  models: {
    title: 'Model Settings',
    description: 'Configure which AI models to use for indexing and queries',
    keys: ['indexing_model', 'query_model', 'embedding_model'],
  },
  graphrag: {
    title: 'GraphRAG Settings',
    description: 'Fine-tune GraphRAG behavior',
    keys: ['chunk_size', 'chunk_overlap', 'community_level'],
  },
  ratelimits: {
    title: 'Rate Limiting',
    description: 'Control API request rates to avoid hitting limits',
    keys: ['concurrent_requests', 'requests_per_minute', 'tokens_per_minute'],
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResults, setTestResults] = useState<ConnectionTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Add timeout to prevent infinite loading
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      const data = await getSettings();
      clearTimeout(timeoutId);

      setSettings(data);

      // Initialize form values
      const values: Record<string, string> = {};
      for (const [key, setting] of Object.entries(data.settings)) {
        if (setting.sensitive && setting.has_value) {
          values[key] = ''; // Don't show masked values
        } else {
          values[key] = setting.value?.toString() || '';
        }
      }
      setFormValues(values);
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') {
        setError('Backend is not responding. It may be busy indexing documents. Please wait and try again.');
      } else {
        setError(e instanceof Error ? e.message : 'Failed to load settings');
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // Only send values that have changed or have content
      const updates: Record<string, string | number | null> = {};
      for (const [key, value] of Object.entries(formValues)) {
        const setting = settings?.settings[key];
        if (!setting) continue;

        // Skip empty sensitive fields (means keep existing value)
        if (setting.sensitive && !value) continue;

        // Convert integers
        if (setting.type === 'integer' && value) {
          updates[key] = parseInt(value, 10);
        } else if (value) {
          updates[key] = value;
        }
      }

      const result = await updateSettings(updates);

      if (result.success) {
        toast.success('Settings saved', {
          description: `Updated ${result.updated.length} setting(s)`,
        });
        fetchSettings(); // Refresh to get updated masked values
      } else {
        const errorMessages = Object.entries(result.errors)
          .map(([k, v]) => `${k}: ${v}`)
          .join(', ');
        toast.error('Some settings failed to save', {
          description: errorMessages,
        });
      }
    } catch (e) {
      toast.error('Failed to save settings', {
        description: e instanceof Error ? e.message : 'Unknown error',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestConnections = async () => {
    setIsTesting(true);
    setTestResults(null);
    try {
      const results = await testConnections();
      setTestResults(results);

      if (results.paperless.success && results.litellm.success) {
        toast.success('All connections successful');
      } else {
        toast.warning('Some connections failed');
      }
    } catch (e) {
      toast.error('Failed to test connections', {
        description: e instanceof Error ? e.message : 'Unknown error',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const renderSettingInput = (key: string, setting: SettingValue) => {
    const isVisible = showSensitive[key] || !setting.sensitive;
    const currentValue = formValues[key] || '';
    const placeholder = setting.sensitive && setting.has_value
      ? '(configured - leave empty to keep)'
      : setting.default?.toString() || '';

    return (
      <div key={key} className="space-y-2">
        <div className="flex items-center justify-between">
          <Label htmlFor={key} className="flex items-center gap-2">
            {setting.label}
            {setting.required && <Badge variant="destructive" className="text-xs">Required</Badge>}
          </Label>
          {setting.sensitive && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSensitive((prev) => ({ ...prev, [key]: !prev[key] }))}
            >
              {isVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
          )}
        </div>
        <Input
          id={key}
          type={setting.sensitive && !isVisible ? 'password' : setting.type === 'integer' ? 'number' : 'text'}
          value={currentValue}
          onChange={(e) => setFormValues((prev) => ({ ...prev, [key]: e.target.value }))}
          placeholder={placeholder}
          min={setting.min}
          max={setting.max}
          className="shadow-sm"
        />
        {setting.type === 'integer' && (setting.min !== undefined || setting.max !== undefined) && (
          <p className="text-xs text-muted-foreground">
            Range: {setting.min ?? 'any'} - {setting.max ?? 'any'}
            {setting.default !== undefined && ` (default: ${setting.default})`}
          </p>
        )}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[50vh]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-8">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
            Settings
          </h1>
          <p className="text-muted-foreground text-lg">
            Configure your Paperless GraphRAG installation
          </p>
        </div>
        <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-destructive/5">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <XCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
            <Button onClick={fetchSettings} className="mt-4">
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-foreground via-foreground to-primary bg-clip-text text-transparent">
            Settings
          </h1>
          <p className="text-muted-foreground text-lg">
            Configure your Paperless GraphRAG installation
          </p>
        </div>
        <div className="flex items-center gap-2">
          {settings?.is_configured ? (
            <Badge variant="default" className="bg-green-500">
              <CheckCircle className="h-3 w-3 mr-1" />
              Configured
            </Badge>
          ) : (
            <Badge variant="destructive">
              <AlertCircle className="h-3 w-3 mr-1" />
              Setup Required
            </Badge>
          )}
        </div>
      </div>

      {settings?.missing_required && settings.missing_required.length > 0 && (
        <Card className="shadow-lg border-0 bg-gradient-to-br from-card to-yellow-500/10">
          <CardContent className="pt-6">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-yellow-500 mt-0.5" />
              <div>
                <p className="font-medium">Missing Required Settings</p>
                <p className="text-sm text-muted-foreground">
                  Configure the following to use all features:{' '}
                  {settings.missing_required.map((k) => settings.settings[k]?.label || k).join(', ')}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="space-y-6">
        {Object.entries(SETTING_GROUPS).map(([groupKey, group]) => (
          <Card key={groupKey} className="shadow-lg border-0 bg-gradient-to-br from-card to-card/80">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <SettingsIcon className="h-5 w-5 text-primary" />
                {group.title}
              </CardTitle>
              <CardDescription>{group.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {group.keys.map((key) => {
                const setting = settings?.settings[key];
                if (!setting) return null;
                return renderSettingInput(key, setting);
              })}

              {groupKey === 'connections' && (
                <>
                  <Separator className="my-4" />
                  <div className="flex items-center gap-4">
                    <Button
                      variant="secondary"
                      onClick={handleTestConnections}
                      disabled={isTesting || !settings?.is_configured}
                    >
                      {isTesting ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <RefreshCw className="h-4 w-4 mr-2" />
                      )}
                      Test Connections
                    </Button>

                    {testResults && (
                      <div className="flex gap-4 text-sm">
                        <div className="flex items-center gap-1">
                          {testResults.paperless.success ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-destructive" />
                          )}
                          <span>Paperless</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {testResults.litellm.success ? (
                            <CheckCircle className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-destructive" />
                          )}
                          <span>LiteLLM</span>
                        </div>
                      </div>
                    )}
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="flex justify-end gap-4 sticky bottom-4 bg-background/80 backdrop-blur-sm p-4 rounded-xl shadow-lg">
        <Button variant="outline" onClick={fetchSettings} disabled={isSaving}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Reset
        </Button>
        <Button onClick={handleSave} disabled={isSaving} className="shadow-md">
          {isSaving ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save Settings
        </Button>
      </div>
    </div>
  );
}
