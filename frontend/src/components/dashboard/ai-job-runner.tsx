"use client";

import { useEffect, useMemo, useState } from 'react';
import { Loader2, RotateCcw, Sparkles } from 'lucide-react';
import { aiJobsApi } from '@/lib/api/ai-jobs';
import type { AIJobResponse } from '@/schemas/ai-job.schemas';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

const POLL_INTERVAL_MS = 2000;

export function AIJobRunner() {
  const [job, setJob] = useState<AIJobResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [requestCount, setRequestCount] = useState(0);

  const canRetry = job?.status === 'failed' || job?.status === 'timed_out';
  const isTerminal = useMemo(() => (job ? aiJobsApi.isTerminal(job.status) : false), [job]);

  async function submitJob() {
    setIsSubmitting(true);
    try {
      const nextJob = await aiJobsApi.submit({
        action: 'summarize',
        prompt: 'Create a concise executive summary for the current document set.',
        document_ids: ['demo-document'],
        metadata: { source: 'dashboard-runner', request_count: requestCount + 1 },
      });
      setJob(nextJob);
      setRequestCount((value) => value + 1);
    } finally {
      setIsSubmitting(false);
    }
  }

  useEffect(() => {
    if (!job || isTerminal) {
      return;
    }

    const handle = window.setInterval(async () => {
      const latest = await aiJobsApi.getStatus(job.job_id);
      setJob(latest);
    }, POLL_INTERVAL_MS);

    return () => window.clearInterval(handle);
  }, [job, isTerminal]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>AI jobs</CardTitle>
        <CardDescription>Submit a real backend AI job and watch live polling-first status updates.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-3">
          <Button onClick={submitJob} disabled={isSubmitting || (job !== null && !isTerminal)}>
            {isSubmitting ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
            Run AI summary
          </Button>
          {canRetry ? (
            <Button variant="outline" onClick={submitJob}>
              <RotateCcw className="size-4" />
              Retry
            </Button>
          ) : null}
        </div>

        {job ? (
          <div className="rounded-[12px] border p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium">{job.action}</p>
                <p className="text-xs text-muted-foreground">Job ID: {job.job_id}</p>
              </div>
              <Badge variant={job.status === 'succeeded' ? 'default' : 'secondary'}>{job.status}</Badge>
            </div>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>Progress: {job.progress}%</p>
              <p>Attempt: {job.attempt} / {job.max_attempts}</p>
              {job.error_payload ? <pre className="overflow-x-auto rounded bg-muted p-2 text-xs">{JSON.stringify(job.error_payload, null, 2)}</pre> : null}
              {job.result_payload ? <pre className="overflow-x-auto rounded bg-muted p-2 text-xs">{JSON.stringify(job.result_payload, null, 2)}</pre> : null}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">No live AI job yet. Start one from the button above.</p>
        )}
      </CardContent>
    </Card>
  );
}
