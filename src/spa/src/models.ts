export interface EntityLocation {
  page_num: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
}

export interface Entity {
  type: string;
  value: string;
  location?: EntityLocation;
}
