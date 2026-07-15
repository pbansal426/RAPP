import { notFound } from 'next/navigation';
import Link from 'next/link';
import { ARTICLES, getArticleBySlug } from '../articles';

export function generateStaticParams() {
  return ARTICLES.map((a) => ({ slug: a.slug }));
}

export default function ArticlePage({ params }: { params: { slug: string } }) {
  const article = getArticleBySlug(params.slug);
  if (!article) {
    notFound();
  }

  return (
    <main className="hub-article-page">
      <Link href="/hub" className="hub-back-link">
        Back to Knowledge Hub
      </Link>

      <span className="hub-card-category">{article.category}</span>
      <h1 className="hub-article-title">{article.title}</h1>
      <p className="hub-article-meta">{article.readMinutes} min read</p>

      <div className="hub-article-body">
        {article.body.map((paragraph, i) => (
          <p key={i}>{paragraph}</p>
        ))}
      </div>

      {article.relatedTemplateCategory && (
        <div className="hub-article-cta">
          <p>Ready to fix this yourself? Get a VIN-exact diagnosis and step-by-step guide.</p>
          <Link href="/" className="hub-article-cta-btn">
            Start My Diagnosis
          </Link>
        </div>
      )}
    </main>
  );
}
