"use client";

import Image from "next/image";

const LOGO_SRC = "/brand/logoCureCompass.png";

/** Same pixel cap and height for header and footer */
export const brandLogoBarClassName =
  "h-16 w-auto max-w-[min(340px,82vw)] object-contain object-left md:h-[4.25rem] md:max-w-[min(420px,50vw)]";

type BrandLogoProps = {
  priority?: boolean;
  className?: string;
};

export function BrandLogo({
  priority,
  className = "h-11 w-auto max-w-[min(280px,78vw)] object-contain object-left md:h-14 md:max-w-[min(340px,42vw)]",
}: BrandLogoProps) {
  return (
    <Image
      src={LOGO_SRC}
      alt="CureCompass — clear answers, real progress, hope for the journey"
      width={340}
      height={110}
      className={className}
      priority={priority}
      sizes="(max-width: 768px) 78vw, 340px"
    />
  );
}
