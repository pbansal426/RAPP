export interface Article {
  slug: string;
  title: string;
  category: 'Maintenance' | 'Diagnostics' | 'Buying a Guide' | 'Safety';
  summary: string;
  readMinutes: number;
  relatedTemplateCategory?: string;
  body: string[]; // one paragraph per array entry, rendered as <p>
}

export const ARTICLES: Article[] = [
  {
    slug: 'is-my-mechanic-quote-fair',
    title: 'Is My Mechanic Quote Fair? How to Tell in 5 Minutes',
    category: 'Buying a Guide',
    summary:
      'The three numbers on any repair quote that separate a fair price from an overcharge, and where to find them for your exact vehicle.',
    readMinutes: 4,
    body: [
      'A repair quote has three components: parts, labor hours, and labor rate. Most overcharges hide in the labor-hours number, not the labor rate -- a shop quoting 4 hours for a job that takes an experienced tech 1.5 hours is the single most common way estimates get inflated.',
      'Independent shops typically bill $110-$140/hr; dealerships $180-$220/hr. Neither is inherently wrong -- dealerships carry OEM-trained technicians and genuine parts overhead -- but you should know which one you are paying for and why.',
      'Parts markup is normal (30-50% at a dealership, 10-20% at an independent shop covers sourcing, warranty, and inventory risk) but should track the part\'s actual retail price, not an arbitrary multiple of it.',
      'The fastest sanity check: get your VIN-exact diagnosis and cost breakdown from RAPP before you approve any quote. It shows the same three numbers -- parts, labor hours, and a dealer/independent/DIY cost range -- sourced from your car\'s actual specs, not a shop\'s estimate.',
    ],
  },
  {
    slug: 'oil-change-interval-myths',
    title: 'The 3,000-Mile Oil Change Myth (And What Your Car Actually Needs)',
    category: 'Maintenance',
    summary:
      'Most modern engines go 5,000-10,000 miles between changes. Here is how to find your actual interval instead of guessing.',
    readMinutes: 3,
    relatedTemplateCategory: 'oil_service',
    body: [
      'The 3,000-mile rule dates to conventional oil formulations from decades ago. Modern full-synthetic oils and tighter engine tolerances routinely support 5,000-10,000 mile intervals, and many vehicles now use an oil-life monitor that reads actual driving conditions instead of a flat mileage number.',
      'Your owner\'s manual (or the sticker on your driver\'s door jamb) lists the manufacturer interval for your specific engine and oil grade -- that number, not a generic rule of thumb, is the one to follow.',
      'Severe-use conditions (frequent short trips under 10 minutes, towing, extreme heat or cold, dusty roads) shorten the safe interval. If most of your driving fits that profile, follow the manual\'s "severe service" schedule instead of the normal one.',
      'Changing your own oil is one of the lowest-risk, highest-value DIY jobs on this list -- no special tools beyond a wrench, drain pan, and filter wrench, and it typically costs a third of a shop\'s price in parts alone.',
    ],
  },
  {
    slug: 'wiper-blades-when-to-replace',
    title: 'Streaky Wipers? Here\'s How to Tell If It\'s the Blades or the Glass',
    category: 'Maintenance',
    summary:
      'Streaking, skipping, and chatter usually mean the rubber edge has hardened -- a 10-minute, no-tools-beyond-your-hands fix.',
    readMinutes: 2,
    relatedTemplateCategory: 'wiper_blades',
    body: [
      'Wiper rubber hardens and cracks from UV exposure over 6-12 months regardless of mileage, which is why "the blades are only a year old" doesn\'t rule them out as the cause of streaking.',
      'A quick test: run the wipers dry for one pass. If you see a consistent streak along the entire blade length, it\'s almost always the rubber edge, not the glass. Chatter (a juddering, skipping motion) usually means the blade has lost its factory curvature and is no longer applying even pressure.',
      'Most vehicles use a tool-free push-tab connector -- no wrench or screwdriver required, and the whole swap for both blades takes under 10 minutes.',
      'Replace both front blades together even if only one is streaking; they wear at close to the same rate and a mismatched pair often reveals the second failure within weeks.',
    ],
  },
  {
    slug: 'check-engine-light-first-steps',
    title: 'Check Engine Light On? Do This Before You Panic (or Pay for Diagnostics)',
    category: 'Diagnostics',
    summary:
      'A steady light and a flashing light mean very different things. Here is what to check yourself before booking a shop visit.',
    readMinutes: 4,
    body: [
      'A flashing check engine light signals an active misfire that can damage your catalytic converter within minutes of continued driving -- reduce speed and get off the road as soon as safely possible. A steady light is not an emergency and is safe to drive on while you investigate.',
      'The most common trigger by far is a loose or failing gas cap, which sets an EVAP-system code. Tighten the cap until it clicks 3 times and see if the light clears after a few drive cycles before assuming anything is actually broken.',
      'A $15-$25 OBD-II Bluetooth adapter paired with a free phone app reads the exact stored code in under a minute -- that code (e.g. "P0420") is the single most useful piece of information for figuring out what\'s actually wrong, and most auto parts stores will also read it for free.',
      'Once you have a code (or a symptom description even without one), RAPP\'s free diagnosis matches it against your exact VIN and gives you a plain-language root cause plus a fair-price repair estimate before you spend anything on a shop\'s diagnostic fee.',
    ],
  },
  {
    slug: 'airbag-ev-fuel-line-professional-only',
    title: 'Three Systems You Should Never DIY (And Why)',
    category: 'Safety',
    summary:
      'Airbag/SRS, high-voltage EV batteries, and pressurized fuel lines carry injury risk that outweighs any DIY savings. Here is why RAPP refuses to guide you through them.',
    readMinutes: 3,
    body: [
      'Airbag and SRS systems store pyrotechnic charges that can deploy unexpectedly during disassembly, causing severe burns or worse, even with the battery disconnected -- some systems retain enough capacitor charge to fire for minutes afterward.',
      'Hybrid and EV high-voltage battery packs run at 200-800V DC -- roughly 10-40x household voltage -- and improper handling can be fatal. This work requires insulated tools, PPE rated for the voltage class, and manufacturer lockout procedures, not a home garage setup.',
      'Pressurized fuel lines, especially on direct-injection engines, can hold hundreds of PSI even with the engine off. An uncontrolled release can atomize fuel into a flammable mist near hot engine components.',
      'RAPP\'s diagnosis still tells you what\'s wrong and roughly what it should cost -- the step-by-step guide is what gets replaced with a "professional service required" screen and a link to a certified shop, so you still walk in informed instead of guessing.',
    ],
  },
  {
    slug: 'tire-pressure-tpms-explained',
    title: 'TPMS Light On? It\'s Not Always a Slow Leak',
    category: 'Maintenance',
    summary:
      'Temperature swings alone can trigger the TPMS light. Here is how to tell a real leak from a seasonal false alarm.',
    readMinutes: 2,
    relatedTemplateCategory: 'tire_pressure',
    body: [
      'Tire pressure drops roughly 1 PSI for every 10°F the outside temperature falls. A sharp overnight cold snap can trigger the TPMS light on all four tires simultaneously with no actual leak -- that pattern (all four, right after a temperature drop) is the signature of a seasonal false alarm, not a puncture.',
      'A single tire consistently low week after week, especially if it needs air more often than the others, points to a slow leak -- often a small nail or a corroded valve stem, both inexpensive fixes.',
      'Always check and set pressure to the number on your driver\'s door jamb placard, not the number printed on the tire\'s sidewall -- the sidewall number is the tire\'s maximum rating, not your vehicle\'s recommended setting.',
      'After any pressure correction, many vehicles need a manual TPMS relearn procedure (not just driving around) before the warning light clears -- check your owner\'s manual for the reset sequence specific to your vehicle.',
    ],
  },
];

export function getArticleBySlug(slug: string): Article | undefined {
  return ARTICLES.find((a) => a.slug === slug);
}
