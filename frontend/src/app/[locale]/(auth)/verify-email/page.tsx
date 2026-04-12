'use client';

import { useEffect, useState, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Mail, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from '@/lib/i18n/navigation';
import { Button } from '@/components/ui/button';
import { authApi } from '@/lib/api/auth';

const RESEND_COOLDOWN_SECONDS = 60;

/** Inner component that reads useSearchParams — must be inside Suspense. */
function VerifyEmailContent() {
  const t = useTranslations('Auth.verification');
  const searchParams = useSearchParams();
  const token = searchParams.get('token');
  const email = searchParams.get('email') ?? '';

  const [verifying, setVerifying] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [cooldown, setCooldown] = useState(0);
  const [resending, setResending] = useState(false);

  // Auto-verify when token is in URL
  useEffect(() => {
    if (!token) return;
    setVerifying(true);
    authApi
      .verifyEmail(token)
      .then(() => {
        setVerifyStatus('success');
        toast.success('Email verified! You can now sign in.');
      })
      .catch(() => {
        setVerifyStatus('error');
        toast.error('Verification failed. The link may have expired.');
      })
      .finally(() => setVerifying(false));
  }, [token]);

  // Countdown timer for resend cooldown
  useEffect(() => {
    if (cooldown <= 0) return;
    const id = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(id);
  }, [cooldown]);

  const handleResend = useCallback(async () => {
    if (!email || cooldown > 0) return;
    setResending(true);
    try {
      await authApi.resendVerification(email);
      toast.success(t('resendSuccess'));
      setCooldown(RESEND_COOLDOWN_SECONDS);
    } catch {
      toast.error('Failed to resend. Please try again.');
    } finally {
      setResending(false);
    }
  }, [email, cooldown, t]);

  // Token verification in progress
  if (token && verifying) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Verifying your email…</p>
      </div>
    );
  }

  // Token verification result
  if (token && verifyStatus !== 'idle') {
    return (
      <div className="flex flex-col items-center gap-6 text-center">
        <div
          className={`rounded-full p-4 ${
            verifyStatus === 'success' ? 'bg-green-100' : 'bg-red-100'
          }`}
        >
          <Mail
            className={`h-10 w-10 ${
              verifyStatus === 'success' ? 'text-green-600' : 'text-red-600'
            }`}
          />
        </div>
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">
            {verifyStatus === 'success' ? 'Email verified!' : 'Verification failed'}
          </h1>
          <p className="text-sm text-muted-foreground">
            {verifyStatus === 'success'
              ? 'Your account is now active. You can sign in.'
              : 'This link may have expired or already been used.'}
          </p>
        </div>
        <Link href="/login">
          <Button className="h-11 w-full">{t('backToLogin')}</Button>
        </Link>
      </div>
    );
  }

  // Default: check-your-email notice with resend
  return (
    <div className="flex flex-col items-center gap-6 text-center">
      {/* Mail icon — 64px, primary color */}
      <div className="rounded-full bg-primary/10 p-5">
        <Mail className="h-10 w-10 text-primary" />
      </div>

      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">{t('title')}</h1>
        <p className="text-sm text-muted-foreground">
          {email
            ? t('body', { email })
            : 'Click the link in your email to activate your account.'}
        </p>
      </div>

      {/* Resend button with 60s cooldown */}
      <Button
        variant="outline"
        className="h-11 w-full"
        onClick={handleResend}
        disabled={resending || cooldown > 0 || !email}
      >
        {resending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
        {cooldown > 0 ? `${t('resendButton')} (${cooldown}s)` : t('resendButton')}
      </Button>

      <Link
        href="/login"
        className="text-sm text-muted-foreground hover:text-foreground hover:underline"
      >
        {t('backToLogin')}
      </Link>
    </div>
  );
}

/**
 * Email verification page — wrapped in Suspense for useSearchParams().
 * Auto-verifies if ?token= present; shows resend UI otherwise.
 */
export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<div className="h-64 animate-pulse rounded-lg bg-muted" />}>
      <VerifyEmailContent />
    </Suspense>
  );
}
