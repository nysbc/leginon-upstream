<?
include ("inc/jpgraph.php");
include ("inc/jpgraph_line.php");
include ("inc/jpgraph_scatter.php");
include ("inc/jpgraph_bar.php");
include ("inc/histogram.inc");
require ("inc/leginon.inc");
require ("inc/image.inc");

$defaultId= 1445;
$sessionId= ($_GET[Id]) ? $_GET[Id] : $defaultId;
$width = $_GET['w'];
$height = $_GET['h'];
$viewdata = $_GET[vd];
$viewsql = $_GET[vs];


$data = $leginondata->getDriftedImages($sessionId);
foreach ($data as $d) {
	$ids[]=$d['imageId'];
}
if ($dt = $leginondata->getDriftTime($ids)) {
	foreach ($dt as $d) {
		$datay[] = $d['total'];
		$total += $d['total'];
	}
	if ($total)
		$total .= " (s)";
}
if ($viewsql) {
	$sql = $leginondata->mysql->getSQLQuery();
	echo $sql;
	exit;
}
if ($viewdata) {
	echo dumpData($dt);
	exit;
}
if (!$datay) {
	$width = 12;
	$height = 12;
	$source = blankimage($width,$height);
} else {
	$histogram = new histogram($datay);
	$histogram->setBarsNumber(15);
	$rdata = $histogram->getData();
	$rdatax = $rdata['x'];
	$rdatay = $rdata['y'];


	$graph = new Graph(600,400,"auto");    
	$graph->SetScale("linlin");

	$graph->img->SetMargin(40,30,20,40);

	$bplot = new BarPlot($rdatay, $rdatax);
	$graph->Add($bplot);

	$graph->title->Set("Total Drift settling time: $total");
	$graph->xaxis->title->Set("drift time(s)");
	$graph->yaxis->title->Set("Frequency");
	$source = $graph->Stroke(_IMG_HANDLER);
}
resample($source, $width, $height);
?>

