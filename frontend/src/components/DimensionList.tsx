import type { Dimensions } from '../types'
export function DimensionList({ dimensions }: { dimensions: Dimensions }) { return <dl className="dimensions"><div><dt>Ancho</dt><dd>{dimensions.width_cm} cm</dd></div><div><dt>Alto</dt><dd>{dimensions.height_cm} cm</dd></div><div><dt>Profundidad</dt><dd>{dimensions.depth_cm} cm</dd></div></dl> }
