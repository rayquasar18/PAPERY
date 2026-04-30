import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { adminApi } from '@/lib/api/admin';

export default async function AdminTiersPage() {
  let tiers = [] as Awaited<ReturnType<typeof adminApi.listTiers>>;
  try {
    tiers = await adminApi.listTiers();
  } catch {
    tiers = [];
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Tiers</CardTitle>
        <CardDescription>Production-ready basic tier configuration surface.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {tiers.length ? tiers.map((tier: (typeof tiers)[number]) => (
          <div key={tier.uuid} className="rounded-[12px] border p-3">
            <p className="font-medium">{tier.name}</p>
            <p className="text-sm text-muted-foreground">
              {tier.max_projects} projects · {tier.allowed_models.join(', ') || 'No models'}
            </p>
          </div>
        )) : <p className="text-sm text-muted-foreground">Unable to load tiers in this environment.</p>}
      </CardContent>
    </Card>
  );
}
