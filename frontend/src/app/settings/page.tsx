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
  RotateCcw,
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { getSettings, updateSettings, testConnections, restartBackend } from '@/lib/api';
import { testChatConnection } from '@/lib/api/chat';
import { toast } from 'sonner';
import type { SettingsResponse, SettingValue, ConnectionTestResult } from '@/types';
import { Database } from 'lucide-react';

// Settings that require a restart when changed
const RESTART_REQUIRED_SETTINGS = [
  'indexing_model', 'query_model', 'embedding_model',
  'chunk_size', 'chunk_overlap',
  'top_k_entities', 'top_k_relationships', 'text_unit_prop', 'max_tokens',
  'database_url'
];

// Group settings by category
const SETTING_GROUPS: Record<string, {
  title: string;
  description: string;
  keys: string[];
  note?: string;
}> = {
  connections: {
    title: 'Connection Settings',
    description: 'Configure connections to Paperless-ngx and LiteLLM',
    keys: ['paperless_url', 'paperless_token', 'litellm_base_url', 'litellm_api_key'],
  },
  models: {
    title: 'Model Settings',
    description: 'Configure which AI models to use for indexing and queries',
    keys: ['indexing_model', 'query_model', 'embedding_model'],
    note: 'Model changes require a backend restart to take effect.',
  },
  indexing: {
    title: 'Indexing Settings',
    description: 'Configure how documents are processed during indexing',
    keys: ['chunk_size', 'chunk_overlap', 'community_level'],
    note: 'Chunk changes require re-indexing to take effect.',
  },
  search: {
    title: 'Search Settings',
    description: 'Fine-tune how queries search the knowledge graph',
    keys: ['top_k_entities', 'top_k_relationships', 'text_unit_prop', 'max_tokens'],
    note: 'Search settings require a backend restart to take effect.',
  },
  ratelimits: {
    title: 'Rate Limiting',
    description: 'Control API request rates to avoid hitting provider limits',
    keys: ['concurrent_requests', 'requests_per_minute', 'tokens_per_minute'],
  },
  database: {
    title: 'Database Settings',
    description: 'Configure persistent chat history storage (optional)',
    keys: ['database_url'],
    note: 'Leave empty to use browser-local storage only. Requires backend restart after changes.',
  },
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [showSensitive, setShowSensitive] = useState<Record<string, boolean>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isTestingDb, setIsTestingDb] = useState(false);
  const [isRestarting, setIsRestarting] = useState(false);
  const [testResults, setTestResults] = useState<ConnectionTestResult | null>(null);
  const [dbTestResult, setDbTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pendingRestart, setPendingRestart] = useState(false);

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

        // Convert numbers
        if (setting.type === 'integer' && value) {
          updates[key] = parseInt(value, 10);
        } else if (setting.type === 'float' && value) {
          updates[key] = parseFloat(value);
        } else if (value) {
          updates[key] = value;
        }
      }

      const result = await updateSettings(updates);

      if (result.success) {
        // Check if any restart-required settings were updated
        const restartRequired = result.updated.some(key => RESTART_REQUIRED_SETTINGS.includes(key));

        if (restartRequired) {
          setPendingRestart(true);
          toast.success('Settings saved - Restart required', {
            description: 'Click "Apply & Restart" to apply changes.',
            duration: 8000,
          });
        } else {
          toast.success('Settings saved', {
            description: `Updated ${result.updated.length} setting(s)`,
          });
        }
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

  const handleRestart = async () => {
    setIsRestarting(true);
    try {
      await restartBackend();
      toast.success('Restart initiated', {
        description: 'The backend is restarting. Page will reload in a few seconds...',
        duration: 5000,
      });
      // Wait for backend to restart, then reload
      setTimeout(() => {
        setPendingRestart(false);
        window.location.reload();
      }, 3000);
    } catch (e) {
      toast.error('Failed to restart', {
        description: e instanceof Error ? e.message : 'Unknown error',
      });
      setIsRestarting(false);
    }
  };

  const handleTestDatabase = async () => {
    setIsTestingDb(true);
    setDbTestResult(null);
    try {
      const result = await testChatConnection();
      setDbTestResult(result);
      if (result.success) {
        toast.success('Database connection successful');
      } else {
        toast.warning('Database connection failed', {
          description: result.message,
        });
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      setDbTestResult({ success: false, message });
      toast.error('Database test failed', {
        description: message,
      });
    } finally {
      setIsTestingDb(false);
    }
  };

  const renderSettingInput = (key: string, setting: SettingValue) => {
    const isVisible = showSensitive[key] || !setting.sensitive;
    const currentValue = formValues[key] || '';
    const placeholder = setting.sensitive && setting.has_value
      ? '(configured - leave empty to keep)'
      : setting.default?.toString() || '';
    const inputType = setting.sensitive && !isVisible
      ? 'password'
      : (setting.type === 'integer' || setting.type === 'float')
        ? 'number'
        : 'text';
    const step = setting.type === 'float' ? '0.1' : undefined;

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
        {setting.description && (
          <p className="text-xs text-muted-foreground">{setting.description}</p>
        )}
        <Input
          id={key}
          type={inputType}
          step={step}
          value={currentValue}
          onChange={(e) => setFormValues((prev) => ({ ...prev, [key]: e.target.value }))}
          placeholder={placeholder}
          min={setting.min}
          max={setting.max}
          className="shadow-sm"
        />
        {(setting.type === 'integer' || setting.type === 'float') && (setting.min !== undefined || setting.max !== undefined) && (
          <p className="text-xs text-muted-foreground/70">
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
              {group.note && (
                <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1 mt-1">
                  <AlertCircle className="h-3 w-3" />
                  {group.note}
                </p>
              )}
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

              {groupKey === 'database' && (
                <>
                  <Separator className="my-4" />
                  <div className="flex items-center gap-4">
                    <Button
                      variant="secondary"
                      onClick={handleTestDatabase}
                      disabled={isTestingDb}
                    >
                      {isTestingDb ? (
                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      ) : (
                        <Database className="h-4 w-4 mr-2" />
                      )}
                      Test Connection
                    </Button>

                    {dbTestResult && (
                      <div className="flex items-center gap-2 text-sm">
                        {dbTestResult.success ? (
                          <>
                            <CheckCircle className="h-4 w-4 text-green-500" />
                            <span className="text-green-600 dark:text-green-400">Connected</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="h-4 w-4 text-destructive" />
                            <span className="text-muted-foreground">{dbTestResult.message}</span>
                          </>
                        )}
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
        <Button variant="outline" onClick={fetchSettings} disabled={isSaving || isRestarting}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Reset
        </Button>
        <Button onClick={handleSave} disabled={isSaving || isRestarting} className="shadow-md">
          {isSaving ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <Save className="h-4 w-4 mr-2" />
          )}
          Save Settings
        </Button>
        {pendingRestart && (
          <Button
            onClick={handleRestart}
            disabled={isRestarting}
            variant="default"
            className="shadow-md bg-amber-600 hover:bg-amber-700"
          >
            {isRestarting ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <RotateCcw className="h-4 w-4 mr-2" />
            )}
            Apply & Restart
          </Button>
        )}
      </div>
    </div>
  );
}
