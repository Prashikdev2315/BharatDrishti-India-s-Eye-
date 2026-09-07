import { ReactCompareSlider, ReactCompareSliderImage } from "react-compare-slider";
import { thumbnailUrl } from "../api";

export default function CompareSlider({ region, t1Date, t2Date }) {
  return (
    <div className="compare-card">
      <div className="compare-card__header">
        <h2>Before / After</h2>
        <span className="compare-card__dates">
          {t1Date} <span className="arrow">→</span> {t2Date}
        </span>
      </div>
      <div className="compare-card__slider">
        <ReactCompareSlider
          itemOne={
            <ReactCompareSliderImage
              src={thumbnailUrl(region, "t1")}
              alt={`${region} before`}
            />
          }
          itemTwo={
            <ReactCompareSliderImage
              src={thumbnailUrl(region, "t2")}
              alt={`${region} after`}
            />
          }
        />
      </div>
      <div className="compare-card__labels">
        <span>T1 — Before</span>
        <span>T2 — After</span>
      </div>
    </div>
  );
}
