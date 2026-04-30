import { FolderPlus, LayoutGrid, List, Search } from 'lucide-react';
import { hasLocale } from 'next-intl';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { routing } from '@/lib/i18n/routing';

const demoProjects = [
  {
    uuid: '8db55e53-4de8-4e7c-b08e-ef5bf95d31f2',
    name: 'Market rules knowledge base',
    description: 'Shared compliance reference with structured source notes.',
    relationship_type: 'owned',
    updated_at: '2026-04-30T06:15:00Z',
  },
  {
    uuid: '6d9ab539-6779-4cd8-b08e-7019e08ad977',
    name: 'Investor due diligence',
    description: 'Cross-document summaries and citation-backed findings.',
    relationship_type: 'shared',
    updated_at: '2026-04-29T14:45:00Z',
  },
];

type Props = {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ q?: string; sort?: string; view?: string; empty?: string }>;
};

export default async function ProjectsPage({ params, searchParams }: Props) {
  const { locale: rawLocale } = await params;
  const locale = hasLocale(routing.locales, rawLocale) ? rawLocale : routing.defaultLocale;
  setRequestLocale(locale);
  const t = await getTranslations({ locale, namespace: 'Dashboard' });

  const { q = '', sort = 'updated_desc', view = 'list', empty } = await searchParams;
  const isCardView = view === 'cards';
  const isEmpty = empty === 'true';

  const projects = isEmpty
    ? []
    : demoProjects.filter((project) => project.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className="flex flex-col gap-6 p-4 lg:p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <p className="text-sm text-muted-foreground">
          Search, sort, and manage your workspace projects in one place.
        </p>
      </div>

      <div className="flex flex-col gap-3 rounded-[12px] border bg-card p-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-1 items-center gap-2">
          <div className="relative w-full max-w-md">
            <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              defaultValue={q}
              placeholder={t('recentProjects.title')}
              className="pl-9"
              aria-label="Search projects"
            />
          </div>
          <Select defaultValue={sort}>
            <SelectTrigger aria-label="Sort projects">
              <SelectValue placeholder="Sort" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated_desc">Recently updated</SelectItem>
              <SelectItem value="name_asc">Name A–Z</SelectItem>
              <SelectItem value="name_desc">Name Z–A</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Button variant={isCardView ? 'outline' : 'default'} size="sm">
            <List className="size-4" />
            List
          </Button>
          <Button variant={isCardView ? 'default' : 'outline'} size="sm">
            <LayoutGrid className="size-4" />
            Cards
          </Button>
        </div>
      </div>

      {projects.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>{t('emptyState.title')}</CardTitle>
            <CardDescription>{t('emptyState.body')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button>
              <FolderPlus className="size-4" />
              {t('emptyState.cta')}
            </Button>
          </CardContent>
        </Card>
      ) : isCardView ? (
        <div className="grid gap-4 md:grid-cols-2">
          {projects.map((project) => (
            <Card key={project.uuid}>
              <CardHeader>
                <CardTitle>{project.name}</CardTitle>
                <CardDescription>{project.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 text-sm text-muted-foreground">
                <p>Access: {project.relationship_type}</p>
                <p>Updated: {new Date(project.updated_at).toLocaleString(locale)}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="pt-6">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Project</TableHead>
                  <TableHead>Access</TableHead>
                  <TableHead>Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {projects.map((project) => (
                  <TableRow key={project.uuid}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span className="font-medium">{project.name}</span>
                        <span className="text-xs text-muted-foreground">{project.description}</span>
                      </div>
                    </TableCell>
                    <TableCell className="capitalize">{project.relationship_type}</TableCell>
                    <TableCell>{new Date(project.updated_at).toLocaleString(locale)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
