'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useTranslations } from 'next-intl';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
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
import { OAuthButtons } from '@/components/auth/oauth-buttons';
import { loginSchema, type LoginInput } from '@/lib/schemas/auth';
import { useAuth } from '@/lib/hooks/use-auth';

/**
 * Login form — React Hook Form + Zod resolver, validation on blur (D-10).
 * Displays email/password fields, forgot-password link, OAuth buttons,
 * and a register link in the footer.
 */
export function LoginForm() {
  const t = useTranslations('Auth.login');
  const { login, isLoggingIn } = useAuth();
  const [showPassword, setShowPassword] = useState(false);

  const form = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
    mode: 'onBlur',
    defaultValues: {
      email: '',
      password: '',
    },
  });

  async function onSubmit(values: LoginInput) {
    await login(values);
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
          {/* Email */}
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
                    disabled={isLoggingIn}
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Password */}
          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
                <div className="flex items-center justify-between">
                  <FormLabel>{t('passwordLabel')}</FormLabel>
                  <Link
                    href="/forgot-password"
                    className="text-xs text-primary hover:underline"
                    tabIndex={-1}
                  >
                    {t('forgotPassword')}
                  </Link>
                </div>
                <FormControl>
                  <div className="relative">
                    <Input
                      type={showPassword ? 'text' : 'password'}
                      placeholder={t('passwordPlaceholder')}
                      autoComplete="current-password"
                      disabled={isLoggingIn}
                      className="pr-10"
                      {...field}
                    />
                    <button
                      type="button"
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                      onClick={() => setShowPassword((v) => !v)}
                      tabIndex={-1}
                    >
                      {showPassword ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          {/* Submit */}
          <Button
            type="submit"
            className="h-11 w-full"
            disabled={isLoggingIn}
          >
            {isLoggingIn ? (
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

      {/* OAuth buttons */}
      <OAuthButtons />

      {/* Footer — link to register */}
      <p className="text-center text-sm text-muted-foreground">
        {t('noAccount')}{' '}
        <Link href="/register" className="font-medium text-primary hover:underline">
          {t('signUpLink')}
        </Link>
      </p>
    </div>
  );
}
