type DisclaimerBannerProps = {
  disclaimer?: string;
};

const defaultDisclaimer =
  'OncoWatch is an information monitoring and summarization tool. It does not determine treatment, trial eligibility, or medical appropriateness.';

export function DisclaimerBanner({ disclaimer = defaultDisclaimer }: DisclaimerBannerProps) {
  return (
    <div className="disclaimer-banner">
      <div className="disclaimer-banner-label">For clinician review</div>
      <p>{disclaimer} All findings should be reviewed with a licensed oncology team.</p>
    </div>
  );
}
