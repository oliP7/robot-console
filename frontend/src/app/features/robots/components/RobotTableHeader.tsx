export function RobotTableHeader() {
  return (
    <div className="thead" role="rowgroup">
      <div className="row head" role="row" aria-rowindex={1}>
        <div className="cell c-id" role="columnheader">Robot</div>
        <div className="cell c-battery" role="columnheader">Battery</div>
        <div className="cell c-charge" role="columnheader">Charge</div>
        <div className="cell c-mode" role="columnheader">Mode</div>
        <div className="cell c-seen" role="columnheader">Last report</div>
        <div className="cell c-actions" role="columnheader">Actions</div>
      </div>
    </div>
  );
}
