'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Link } from '@/i18n/navigation';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { forgotPasswordSchema, type ForgotPasswordInput } from '@/lib/schemas/auth';
import { authApi } from '@/lib/api/auth';

/**
 * Forgot password form — sends a reset link to the provided email.
 * On success, shows confirmation message instead of the form.
 */
export function ForgotPasswordForm() {
  const t = useTranslations('Auth.forgotPassword');
  const [sent, setSent] = useState(false);
  const [sentEmail, setSentEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const form = useForm<ForgotPasswordInput>({
    resolver: zodResolver(forgotPasswordSchema),
    mode: 'onBlur',
    defaultValues: { email: '' },
  });

  async function onSubmit(values: ForgotPasswordInput) {
    setIsSubmitting(true);
    try {
      await authApi.forgotPassword(values.email);
      setSentEmail(values.email);
      setSent(true);
      toast.success('Reset link sent. Check your email.');
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data
          ?.message ?? 'Failed to send reset link. Please try again.';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  // Success state — confirmation message
  if (sent) {
    return (
      <div className="flex flex-col gap-4 text-center">
        <h1 className="text-2xl font-semibold">{t('successTitle')}</h1>
        <p className="text-sm text-muted-foreground">
          {t('successMessage', { email: sentEmail })}
        </p>
        <Link
          href="/login"
          className="text-sm text-primary hover:underline"
        >
          {t('backToLogin')}
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
        <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>{t('emailLabel')}</FormLabel>
                <FormControl>
                  <Input
                    type="email"
                    placeholder={t('emailPlaceholder')}
                    autoComplete="email"
                    autoFocus
                    disabled={isSubmitting}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <Button
            type="submit"
            className="h-11 w-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('submitButton')}
              </>
            ) : (
              t('submitButton')
            )}
          </Button>
        </form>
      </Form>

      <Link
        href="/login"
        className="text-center text-sm text-muted-foreground hover:text-foreground hover:underline"
      >
        {t('backToLogin')}
      </Link>
    </div>
  );
}
