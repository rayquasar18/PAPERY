"use client";

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { projectsApi } from '@/lib/api/projects';
import type { Project } from '@/schemas/project.schemas';

interface ProjectMemberManagerProps {
  project: Project;
}

export function ProjectMemberManager({ project }: ProjectMemberManagerProps) {
  const [message, setMessage] = useState('Use backend member endpoints to manage collaborators.');

  async function handleInvite() {
    try {
      await projectsApi.createInvite(project.uuid, { role: 'viewer', invitee_email: null });
      setMessage('Live invite endpoint reached successfully.');
    } catch {
      setMessage('Invite endpoint rejected the request in this environment.');
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Members for {project.name}</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 text-sm text-muted-foreground">
        <p>{message}</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleInvite}>Create invite</Button>
          <Button variant="outline" size="sm">Refresh members</Button>
        </div>
      </CardContent>
    </Card>
  );
}
