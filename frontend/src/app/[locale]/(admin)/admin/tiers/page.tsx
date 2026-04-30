import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const tierDrafts = [
  { name: 'Free', limit: '3 projects', models: 'basic' },
  { name: 'Pro', limit: '20 projects', models: 'premium' },
  { name: 'Enterprise', limit: 'Unlimited', models: 'all models' },
];

export default function AdminTiersPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Tiers</CardTitle>
        <CardDescription>Production-ready basic tier configuration surface.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {tierDrafts.map((tier) => (
          <div key={tier.name} className="rounded-[12px] border p-3">
            <p className="font-medium">{tier.name}</p>
            <p className="text-sm text-muted-foreground">{tier.limit} · {tier.models}</p>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
