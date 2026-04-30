import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { adminApi } from '@/lib/api/admin';

export default async function AdminUsersPage() {
  let users = null;
  try {
    users = await adminApi.listUsers();
  } catch {
    users = null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Users</CardTitle>
        <CardDescription>Core list/detail surface for user administration.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {users?.items?.length ? users.items.slice(0, 10).map((user: (typeof users.items)[number]) => (
          <div key={user.uuid} className="rounded-[12px] border p-3">
            <p className="font-medium">{user.email}</p>
            <p className="text-sm text-muted-foreground">{user.status} · superuser: {String(user.is_superuser)}</p>
          </div>
        )) : <p className="text-sm text-muted-foreground">Unable to load users in this environment.</p>}
      </CardContent>
    </Card>
  );
}
