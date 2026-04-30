import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { adminApi } from '@/lib/api/admin';

export default async function AdminSettingsPage() {
  let grouped = null;
  try {
    grouped = await adminApi.listSettings();
  } catch {
    grouped = null;
  }

  const sections = grouped ? Object.entries(grouped.settings) : [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>System settings</CardTitle>
        <CardDescription>Runtime configuration grouped by category.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {sections.length ? sections.map(([category, settings]: [string, (typeof sections)[number][1]]) => (
          <div key={category} className="rounded-[12px] border p-3">
            <p className="mb-2 font-medium capitalize">{category}</p>
            <div className="space-y-2">
              {settings.map((setting) => (
                <div key={setting.uuid} className="text-sm text-muted-foreground">
                  <span className="font-medium text-foreground">{setting.key}</span>
                </div>
              ))}
            </div>
          </div>
        )) : <p className="text-sm text-muted-foreground">Unable to load settings in this environment.</p>}
      </CardContent>
    </Card>
  );
}
