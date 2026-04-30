"use client";

import { useEffect, useMemo, useState } from 'react';
import { FolderPlus, LayoutGrid, List, Loader2, Search, UserCog2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import { projectsApi } from '@/lib/api/projects';
import type { Project, ProjectCreateInput } from '@/schemas/project.schemas';
import { ProjectDeleteDialog } from './project-delete-dialog';
import { ProjectFormDialog } from './project-form-dialog';
import { ProjectMemberManager } from './project-member-manager';

interface ProjectsDashboardProps {
  emptyTitle: string;
  emptyBody: string;
  emptyCta: string;
}

export function ProjectsDashboard({ emptyTitle, emptyBody, emptyCta }: ProjectsDashboardProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [search, setSearch] = useState('');
  const [sort, setSort] = useState('updated_desc');
  const [view, setView] = useState<'list' | 'cards'>('list');
  const [loading, setLoading] = useState(true);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);

  async function loadProjects(query = search) {
    setLoading(true);
    try {
      const data = await projectsApi.list({ search: query });
      setProjects(data.items);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProjects('');
  }, []);

  const sortedProjects = useMemo(() => {
    const items = [...projects];
    if (sort === 'name_asc') {
      items.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sort === 'name_desc') {
      items.sort((a, b) => b.name.localeCompare(a.name));
    } else {
      items.sort((a, b) => {
        const left = new Date(a.updated_at ?? a.created_at).getTime();
        const right = new Date(b.updated_at ?? b.created_at).getTime();
        return right - left;
      });
    }
    return items;
  }, [projects, sort]);

  async function handleCreate(values: ProjectCreateInput) {
    await projectsApi.create(values);
    await loadProjects();
  }

  async function handleUpdate(projectUuid: string, values: ProjectCreateInput) {
    await projectsApi.update(projectUuid, values);
    await loadProjects();
  }

  async function handleDelete(projectUuid: string) {
    await projectsApi.remove(projectUuid);
    await loadProjects();
    if (selectedProject?.uuid === projectUuid) {
      setSelectedProject(null);
    }
  }

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
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              onBlur={() => void loadProjects(search)}
              placeholder="Search projects"
              className="pl-9"
              aria-label="Search projects"
            />
          </div>
          <Select value={sort} onValueChange={setSort}>
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
          <Button variant={view === 'list' ? 'default' : 'outline'} size="sm" onClick={() => setView('list')}>
            <List className="size-4" />
            List
          </Button>
          <Button variant={view === 'cards' ? 'default' : 'outline'} size="sm" onClick={() => setView('cards')}>
            <LayoutGrid className="size-4" />
            Cards
          </Button>
          <ProjectFormDialog
            triggerLabel={emptyCta}
            title="Create project"
            description="Create a backend-backed project record."
            submitLabel="Create"
            onSubmit={handleCreate}
          />
        </div>
      </div>

      {loading ? (
        <Card>
          <CardContent className="flex items-center gap-3 pt-6 text-sm text-muted-foreground">
            <Loader2 className="size-4 animate-spin" />
            Loading live projects…
          </CardContent>
        </Card>
      ) : sortedProjects.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>{emptyTitle}</CardTitle>
            <CardDescription>{emptyBody}</CardDescription>
          </CardHeader>
          <CardContent>
            <ProjectFormDialog
              triggerLabel={emptyCta}
              title="Create project"
              description="Create your first live project."
              submitLabel="Create"
              onSubmit={handleCreate}
            />
          </CardContent>
        </Card>
      ) : view === 'cards' ? (
        <div className="grid gap-4 md:grid-cols-2">
          {sortedProjects.map((project) => (
            <Card key={project.uuid}>
              <CardHeader>
                <CardTitle>{project.name}</CardTitle>
                <CardDescription>{project.description}</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3 text-sm text-muted-foreground">
                <p>Access: {project.relationship_type ?? 'owned'}</p>
                <p>Updated: {new Date(project.updated_at ?? project.created_at).toLocaleString()}</p>
                <div className="flex flex-wrap gap-2">
                  <ProjectFormDialog
                    triggerLabel="Edit"
                    title="Edit project"
                    description="Update live project metadata."
                    submitLabel="Save"
                    project={project}
                    onSubmit={(values) => handleUpdate(project.uuid, values)}
                  />
                  <ProjectDeleteDialog
                    projectName={project.name}
                    onConfirm={() => handleDelete(project.uuid)}
                  />
                  <Button variant="outline" size="sm" onClick={() => setSelectedProject(project)}>
                    <UserCog2 className="size-4" />
                    Members
                  </Button>
                </div>
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
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedProjects.map((project) => (
                  <TableRow key={project.uuid}>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        <span className="font-medium">{project.name}</span>
                        <span className="text-xs text-muted-foreground">{project.description}</span>
                      </div>
                    </TableCell>
                    <TableCell className="capitalize">{project.relationship_type ?? 'owned'}</TableCell>
                    <TableCell>{new Date(project.updated_at ?? project.created_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-2">
                        <ProjectFormDialog
                          triggerLabel="Edit"
                          title="Edit project"
                          description="Update live project metadata."
                          submitLabel="Save"
                          project={project}
                          onSubmit={(values) => handleUpdate(project.uuid, values)}
                        />
                        <ProjectDeleteDialog
                          projectName={project.name}
                          onConfirm={() => handleDelete(project.uuid)}
                        />
                        <Button variant="outline" size="sm" onClick={() => setSelectedProject(project)}>
                          <UserCog2 className="size-4" />
                          Members
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {selectedProject ? (
        <ProjectMemberManager project={selectedProject} />
      ) : null}
    </div>
  );
}
