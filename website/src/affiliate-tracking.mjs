const directHostingerPricing = "https://www.hostinger.com/horizons/pricing";
const directHostingerFeatures = "https://www.hostinger.com/horizons/features";

const trackingBaseUrl = (process.env.AFFILIATE_TRACKING_BASE_URL || "").replace(/\/$/, "");
const hostingerEnabled = process.env.HOSTINGER_HORIZONS_AFFILIATE_ENABLED === "1";

const trackedHostingerUrl = (content) =>
  `${trackingBaseUrl}/go/hostinger-horizons?source=website&medium=affiliate&content=${encodeURIComponent(content)}`;

const replaceAnchor = (body, { directHref, label, content }) => {
  if (!hostingerEnabled) return body;
  if (!trackingBaseUrl) {
    throw new Error(
      "HOSTINGER_HORIZONS_AFFILIATE_ENABLED=1 requires AFFILIATE_TRACKING_BASE_URL.",
    );
  }

  const direct = `<a class="button product-cta" href="${directHref}" target="_blank" rel="noopener noreferrer">${label}</a>`;
  const tracked = `<a class="button product-cta" href="${trackedHostingerUrl(content)}" target="_blank" rel="sponsored nofollow noopener noreferrer">${label}</a>`;
  return body.replace(direct, tracked);
};

export const applyAffiliateTracking = (page) => {
  let body = page.body;

  if (page.path === "/ai-app-builders/hostinger-horizons-buyer-guide/") {
    body = replaceAnchor(body, {
      directHref: directHostingerPricing,
      label: "Check Hostinger Horizons current plans",
      content: "hostinger-horizons-buyer-guide",
    });
    if (hostingerEnabled) {
      body = body.replace(
        "This page currently uses direct Hostinger links. If an approved affiliate link is added later, it will be clearly disclosed and marked sponsored.",
        "This page contains a sponsored affiliate link to Hostinger. We may earn a commission from an eligible purchase at no extra cost to you.",
      );
    }
  }

  if (page.path === "/comparisons/lovable-vs-hostinger-horizons/") {
    body = replaceAnchor(body, {
      directHref: directHostingerFeatures,
      label: "Check Hostinger Horizons plans",
      content: "lovable-vs-hostinger-horizons",
    });
  }

  return { ...page, body };
};

export const affiliateTrackingStatus = {
  hostingerEnabled,
  trackingBaseConfigured: Boolean(trackingBaseUrl),
};
