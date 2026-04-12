'use client';

/** Password strength levels and visual indicator. */
type StrengthLevel = 'weak' | 'fair' | 'good' | 'strong';

interface StrengthInfo {
  level: StrengthLevel;
  label: string;
  width: string;
  color: string;
}

function getStrength(password: string): StrengthInfo {
  if (!password || password.length < 8) {
    return { level: 'weak', label: 'Weak', width: 'w-1/4', color: 'bg-red-500' };
  }

  const hasLower = /[a-z]/.test(password);
  const hasUpper = /[A-Z]/.test(password);
  const hasNumber = /\d/.test(password);
  const hasSpecial = /[^a-zA-Z0-9]/.test(password);
  const categoryCount = [hasLower, hasUpper, hasNumber].filter(Boolean).length;

  // Strong: 12+ chars, all 3 categories + special char
  if (password.length >= 12 && categoryCount === 3 && hasSpecial) {
    return { level: 'strong', label: 'Strong', width: 'w-full', color: 'bg-green-500' };
  }

  // Good: 8+ chars, all 3 categories
  if (password.length >= 8 && categoryCount === 3) {
    return { level: 'good', label: 'Good', width: 'w-3/4', color: 'bg-yellow-500' };
  }

  // Fair: 8+ chars, 2 of 3 categories
  if (password.length >= 8 && categoryCount >= 2) {
    return { level: 'fair', label: 'Fair', width: 'w-1/2', color: 'bg-orange-500' };
  }

  return { level: 'weak', label: 'Weak', width: 'w-1/4', color: 'bg-red-500' };
}

interface PasswordStrengthProps {
  password: string;
}

/**
 * Visual password strength indicator.
 * Evaluates strength by length and character category counts.
 */
export function PasswordStrength({ password }: PasswordStrengthProps) {
  if (!password) return null;

  const strength = getStrength(password);

  return (
    <div className="flex flex-col gap-1 mt-1" aria-live="polite" aria-atomic="true">
      {/* Bar track */}
      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-300 ${strength.width} ${strength.color}`}
        />
      </div>
      {/* Label */}
      <p className={`text-xs font-medium ${
        strength.level === 'strong'
          ? 'text-green-600'
          : strength.level === 'good'
          ? 'text-yellow-600'
          : strength.level === 'fair'
          ? 'text-orange-600'
          : 'text-red-600'
      }`}>
        {strength.label}
      </p>
    </div>
  );
}
