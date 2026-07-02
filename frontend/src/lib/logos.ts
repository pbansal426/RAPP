const MAKE_DOMAIN_MAP: Record<string, string> = {
  HONDA: 'honda.com',
  TOYOTA: 'toyota.com',
  FORD: 'ford.com',
  LEXUS: 'lexus.com',
  CHEVROLET: 'chevrolet.com',
  BMW: 'bmw.com',
  NISSAN: 'nissanusa.com',
  SUBARU: 'subaru.com',
  HYUNDAI: 'hyundaiusa.com',
  KIA: 'kia.com',
  MAZDA: 'mazdausa.com',
  VOLKSWAGEN: 'vw.com',
  AUDI: 'audiusa.com',
  'MERCEDES-BENZ': 'mbusa.com',
  JEEP: 'jeep.com',
  RAM: 'ramtrucks.com',
  GMC: 'gmc.com',
  DODGE: 'dodge.com',
  CHRYSLER: 'chrysler.com',
  ACURA: 'acura.com',
  INFINITI: 'infinitiusa.com',
  VOLVO: 'volvocars.com',
  PORSCHE: 'porsche.com',
  TESLA: 'tesla.com',
  MITSUBISHI: 'mitsubishicars.com',
  BUICK: 'buick.com',
  CADILLAC: 'cadillac.com',
  LINCOLN: 'lincoln.com',
};

export function getLogoUrl(make: string | null | undefined): string | null {
  if (!make) return null;
  const domain = MAKE_DOMAIN_MAP[make.trim().toUpperCase()];
  if (!domain) return null;
  return `https://logo.clearbit.com/${domain}?size=96`;
}
