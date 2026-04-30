import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { adminApi } from '@/lib/api/admin';

export default async function AdminRateLimitsPage() {
  let rules = [] as Awaited<ReturnType<typeof adminApi.listRateLimits>>;
  try {
    rules = await adminApi.listRateLimits();
  } catch {
    rules = [];
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rate limits</CardTitle>
        <CardDescription>Basic list/detail surface for endpoint throttling rules.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {rules.length ? rules.map((rule: (typeof rules)[number]) => (
          <div key={rule.uuid} className="rounded-[12px] border p-3">
            <p className="font-medium">{rule.endpoint_pattern}</p>
            <p className="text-sm text-muted-foreground">{rule.max_requests} requests / {rule.window_seconds}s</p>
          </div>
        )) : <p className="text-sm text-muted-foreground">Unable to load rate limit rules in this environment.</p>}
      </CardContent>
    </Card>
  );
}
