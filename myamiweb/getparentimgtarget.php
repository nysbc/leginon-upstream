<?php

/**
 *	The Leginon software is Copyright 2003 
 *	The Scripps Research Institute, La Jolla, CA
 *	For terms of the license agreement
 *	see  http://ami.scripps.edu/software/leginon-license
 */

require('inc/leginon.inc');
require('inc/square.inc');
require('inc/scalebar.inc');
require('inc/filter.inc');

$g=true;
if (!$session=stripslashes($_GET[session])) {
	$g=false;
}
if (!$table=stripslashes($_GET[table])) {
	$table="AcquisitionImageData";
}
if (!$id=stripslashes($_GET[id])) {
	$g=false;
}
if (!$preset=stripslashes($_GET[preset])) {
	// $g=false;
}
$t = $_GET['t'];
if ($t=='png') {
        $type = "image/x-png";
} else {
        $type = "image/jpeg";
	$quality=$t;
}



$minpix = ($_GET['np']) ? $_GET['np'] : 0;
$maxpix = ($_GET['xp']) ? $_GET['xp'] : 255;
$size = $_GET['s'];
$displaytarget = ($_GET['tg']==1) ? true : false;
$displayscalebar = ($_GET['sb']==1) ? true : false;
$fft = ($_GET['fft']==1) ? true : false;
if (!$filter=$_GET['flt']) 
	$filter = 'default';

$displayloadingtime = true;

if ($size) {
	$new_w = $size;
	$new_h = $size;
}

if ($g) {
	// --- get image path
	$path = $leginondata->getImagePath($session);

	// --- find image
	$newimage = $leginondata->findImage($id, $preset);
	$id = $newimage[id];
	$parent = $leginondata->getImageInfo($newimage[childid]);

	// --- get filename
	if ($fft) {
		$displaytarget=false;
		$displayscalebar=false;
		$fft = $leginondata->getImageFFT($id);
		$filename = $fft[fftimage];
	} else {
		$filename = $leginondata->getFilename($id);
	}

	$pic = $path.$filename;
	if (is_file($pic)) {
		$imginfo = $leginondata->getImageInfo($id);
		$dimx = $imginfo[dimx];

		if ($displayloadingtime)
			$begin=getmicrotime();

		if (READ_MRC == "mrcmod") {
			$binning = ($dimx > 1024) ? (($dimx > 2048) ? 4 : 2 ) : 1;
			$filterdata = new filter($pic, $minpix, $maxpix, $binning);
			$img = $filterdata->getFilter($filter);
			if ($size) {
				$scalefactor = (imagesx($img)) ? $size/imagesx($img) : 1;
				imagescale($img, $scalefactor);
			}
		} else {
			require_once('inc/mrc.inc');
			$mrc = new mrc;
			$img = $mrc->imagecreatefromMRC($pic,$new_w,$new_h,$minpix, $maxpix, $quality);
		}

		if ($displayloadingtime)
			$end=getmicrotime();

		$white = imagecolorallocate($img, 255, 255, 255);
		$black = imagecolorallocate($img, 0, 0, 0);
		$blue = imagecolorallocate($img, 0, 255, 255);
		$yellow= imagecolorallocate($img, 255, 255, 0);
	  if ($displaytarget) {
		$targets = $leginondata->getImageTargets($id);
		$line=20;
		$diam=20;
		foreach ($targets as $target) {
			$tId=$target[parentId];
			$targetinfo = $leginondata->getImageInfo($tId);
			$targetcal = $leginondata->getImageMatrixCalibration($tId);
			$parentcal = $leginondata->getImageMatrixCalibration($id);
			$truediam=$targetinfo[targetdiam];
			$truedim=$targetinfo[targetdim];
			if (abs($target[x]-$parent[targetx])<5
				&& abs($target[y]-$parent[targety])<5 ){
				$col = $blue;
				$crosscol = $yellow;
			} else {
				$col = $white;
				$crosscol = $white;
			}
			$tn = $targetinfo[parentnumber];
			$ratioX = ($size) ? $size/$target[dimx] : (($binning) ? 1/$binning : 1);
			$ratioY = ($size) ? $size/$target[dimy] : (($binning) ? 1/$binning : 1);
			$xc = $target[x]*$ratioX;
			$yc = $target[y]*$ratioY;
			$square = new square($xc,$yc, $truedim*$ratioX);
			$angle= $targetcal['angle']-$parentcal['angle'];
			$squarepoints = $square->getRotatedPointCoords($angle);
			$txc = $squarepoints[0]+1;
			$tyc = $squarepoints[1]+1;
			$npoints=count($squarepoints)/2;
			
		}
		$targets = $leginondata->getImageFocusTargets($id);
		$line=20;
		$diam=20;
		$myc=0;
		foreach ($targets as $target) {
			$tgn=$target[parentnumber];
			$tn='focus';
			if (abs($target[x]-$parent[targetx])<5
				&& abs($target[y]-$parent[targety])<5 ){
				$col = $blue;
				$crosscol = $yellow;
			} else {
				$col = $white;
				$crosscol = $white;
			}
			$ratioX = ($size) ? $size/$target[dimx] : (($binning) ? 1/$binning : 1);
			$ratioY = ($size) ? $size/$target[dimy] : (($binning) ? 1/$binning : 1);
			$xc = $target[x]*$ratioX;
			$yc = $target[y]*$ratioY;
			imagearc($img, ($target[x]*$ratioX), ($target[y]*$ratioY), $diam*$ratioX, $diam*$ratioY, 0, 360, $crosscol);
			imageline($img, ($target[x]-$line)*$ratioX, ($target[y]*$ratioY), ($target[x]+$line)*$ratioX, ($target[y]*$ratioY), $crosscol); 
			imageline($img, $target[x]*$ratioX, ($target[y]-$line)*$ratioY, $target[x]*$ratioX, ($target[y]+$line)*$ratioY, $crosscol); 
			imagestring($img, 4, $xc+1, $yc+1, $tn, $black);
			imagestring($img, 4, $xc, $yc, $tn, $col);
			$myc++;
		}
	  }

	/* diplay loading time */
	if ($displayloadingtime) {
		imagestring($img, 4, 11, 11, "load time: ".($end-$begin), $black);
		imagestring($img, 4, 10, 10, "load time: ".($end-$begin), $blue);
	}

	  /* display scale bar */
	  if ($displayscalebar) {
		if ($imginfo) {
			$size = ($size) ? $size : (($binning) ? $imginfo[dimx]/$binning : $imginfo[dimx]);
			$ratio = $imginfo[dimx]/$size ;
			$value = $imginfo[pixelsize]*$imginfo[binning]*$ratio;
			$scalebar = new ScaleBar($img, $size, $value);
			$scalebar->display();
		}
	  }
		Header( "Content-type: $type ");
		if ($t=='png')
			imagepng($img);
		else
			imagejpeg($img,'',$quality);

		imagedestroy($img);
	} else {
		Header("Content-type: image/x-png");
		$blkimg = imagecreate(256,256);
		$white = imagecolorallocate($blkimg, 255, 255, 255);
		imagepng($blkimg);
		imagedestroy($blkimg);
	}
}
?>
