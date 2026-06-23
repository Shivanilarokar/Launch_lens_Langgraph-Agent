export default function ProductCard({ product }) {
  const { title, price, currency, rating, reviews_count, image, asin, best_seller, sales_volume } = product
  return (
    <div className="pcard">
      <div className="pcard-img">
        {image
          ? <img src={image} alt={title} loading="lazy" />
          : <div className="pcard-noimg">📦</div>}
        {best_seller && <span className="pcard-bs">Bestseller</span>}
      </div>
      <div className="pcard-body">
        <div className="pcard-title" title={title}>{title}</div>
        <div className="pcard-meta">
          <span className="pcard-price">{currency || ''} {price != null ? price.toLocaleString('en-IN') : '–'}</span>
          {rating != null && (
            <span className="pcard-rating">
              <span className="stars"><span className="stars-bg">★★★★★</span><span className="stars-fill" style={{ width: `${(rating / 5) * 100}%` }}>★★★★★</span></span>
              <span className="pcard-rev">{reviews_count != null ? reviews_count.toLocaleString('en-IN') : ''}</span>
            </span>
          )}
        </div>
        {sales_volume && <div className="pcard-vol">{sales_volume}</div>}
        <div className="pcard-asin">{asin}</div>
      </div>
    </div>
  )
}
