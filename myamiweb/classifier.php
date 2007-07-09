<?php
/**
 *      The Leginon software is Copyright 2003 
 *      The Scripps Research Institute, La Jolla, CA
 *      For terms of the license agreement
 *      see  http://ami.scripps.edu/software/leginon-license
 *
 *      Simple viewer to view a image using mrcmodule
 */

require ('inc/leginon.inc');
require ('inc/project.inc');
require ('inc/particledata.inc');
require ('inc/viewer.inc');
require ('inc/processing.inc');
require ('inc/ctf.inc');

// IF VALUES SUBMITTED, EVALUATE DATA
if ($_POST['process']) {
        runClassifier();
}

// Create the form page
else {
        createClassifierForm();
}

function createClassifierForm($extra=false, $title='Classifier.py Launcher', $heading='Create an 2D Classification') {
        // check if coming directly from a session
        $expId=$_GET['expId'];
	if ($expId){
	        $sessionId=$expId;
		$projectId=getProjectFromExpId($expId);
		$formAction=$_SERVER['PHP_SELF']."?expId=$expId";
	}
	else {
	        $sessionId=$_POST['sessionId'];
	        $formAction=$_SERVER['PHP_SELF'];
	}
	$projectId=$_POST['projectId'];

	// connect to particle and ctf databases
	$particle = new particledata();
	$ctf = new ctfdata();
	$ctfdata=$ctf->hasCtfData($sessionId);
	$prtlrunIds = $particle->getParticleRunIds($sessionId);
	$stackIds = $particle->getStackIds($sessionId);

	// --- find hosts to run classifier.py
	$hosts=getHosts();

	// --- get list of users
	$users[]=glander;

	// --- make list of file formats
	$fileformats=array('imagic','spider');
	
	$javascript="<script src='js/viewer.js'></script>
        <script LANGUAGE='JavaScript'>
        function enableice(){
          if (document.viewerform.icecheck.checked){
              document.viewerform.ice.disabled=false;
              document.viewerform.ice.value='';
            }
            else {
              document.viewerform.ice.disabled=true;
              document.viewerform.ice.value='0.8';
            }
          }
          function enableace(){
            if (document.viewerform.acecheck.checked){
              document.viewerform.ace.disabled=false;
              document.viewerform.ace.value='';
            }
            else {
              document.viewerform.ace.disabled=true;
              document.viewerform.ace.value='0.8';
            }
          }
          function enableselex(){
            if (document.viewerform.selexcheck.checked){
              document.viewerform.selexonmin.disabled=false;
              document.viewerform.selexonmin.value='';
              document.viewerform.selexonmax.disabled=false;
              document.viewerform.selexonmax.value='';
            }
            else {
              document.viewerform.selexonmin.disabled=true;
              document.viewerform.selexonmin.value='0.5';
              document.viewerform.selexonmax.disabled=true;
              document.viewerform.selexonmax.value='1.0';
            }
          }
          </SCRIPT>\n";
	
	writeTop($title,$heading,$javascript);
	// write out errors, if any came up:
	if ($extra) {
	        echo "<FONT COLOR='RED'>$extra</FONT>\n<HR>\n";
	}
  
	echo"
       <FORM NAME='viewerform' method='POST' ACTION='$formAction'>\n";
        $sessiondata=displayExperimentForm($projectId,$sessionId,$expId);
        $sessioninfo=$sessiondata['info'];
        if (!empty($sessioninfo)) {
                $sessionpath=$sessioninfo['Image path'];
                $sessionpath=ereg_replace("leginon","appion",$sessionpath);
                $sessionpath=ereg_replace("rawdata","classes/",$sessionpath);
                $sessionname=$sessioninfo['Name'];
        }

        // Set any existing parameters in form
        $runidval = ($_POST['runid']) ? $_POST['runid'] : 'class1';
        $rundescrval = $_POST['description'];
        $stackidval = $_POST['stackid'];
        $sessionpathval = ($_POST['outdir']) ? $_POST['outdir'] : $sessionpath;
        $commitcheck = ($_POST['commit']=='on') ? 'CHECKED' : '';
        // classifier params
        $numclass = 40;
        $numpart = 3000;
        echo"
        <P>
        <TABLE BORDER=0 CLASS=tableborder>
        <TR>
                <TD VALIGN='TOP'>
                <TABLE CELLPADDING='10' BORDER='0'>
                <TR>
                        <TD VALIGN='TOP'>
                        <A HREF=\"javascript:infopopup('runid')\"><B>Class Run Name:</B></A>
                        <INPUT TYPE='text' NAME='runid' VALUE='$runidval'>
                        </TD>
                </TR>\n";
                //echo"<TR>
                //        <TD VALIGN='TOP'>
                //        <B>Class Description:</B><BR>
                //        <TEXTAREA NAME='description' ROWS='3' COLS='36'>$rundescrval</TEXTAREA>
                //        </TD>
                //</TR>\n";
                echo"<TR>
                        <TD VALIGN='TOP'>         
                        <B>Output Directory:</B><BR>
                        <INPUT TYPE='text' NAME='outdir' VALUE='$sessionpathval' SIZE='38'>
                        </TD>
                </TR>
                <TR>
                        <TD>\n";

        $prtlruns=count($prtlrunIds);

        if (!$stackIds) {
                echo"
                <FONT COLOR='RED'><B>No Stacks for this Session</B></FONT>\n";
        }
        else {
                echo "
                Particles:<BR>
                <SELECT NAME='stackid'>\n";
                foreach ($stackIds as $stack) {
                        // echo divtitle("Stack Id: $stack[stackid]");
                        $stackparams=$particle->getStackParams($stack[stackid]);
                        $runname=$stackparams['stackRunName'];
                        $totprtls=commafy($particle->getNumStackParticles($stack[stackid]));
                        echo "<OPTION VALUE='$stack[stackid]'";
                        // select previously set prtl on resubmit
                        if ($stackidval==$stackid) echo " SELECTED";
                        echo">$runname ($totprtls prtls)</OPTION>\n";
                }
                echo "</SELECT>\n";
        }
        echo"
                </SELECT><BR>
                </TD>
        </TR>
        <TR>
                <TD VALIGN='TOP'>
                <INPUT TYPE='checkbox' NAME='commit' $commitcheck DISABLED>
                <FONT COLOR='gray'>Commit to Database</FONT><BR>
                </TD>
        </TR>\n";
        //echo"<TR>
        //        <TD VALIGN='TOP'>
        //        <B>File Format:</B><BR>
        //        <SELECT NAME='fileformat'>\n";
        //foreach($fileformats as $format) {
        //        $s = ($_POST['fileformat']==$format) ? 'SELECTED' : '';
        //        echo "<OPTION $s >$format</option>\n";
        //}";
        echo"
        </TABLE>
        </TD>
        <TD CLASS='tablebg'>
        <TABLE CELLPADDING='5' BORDER='0'>
        <TR>
                <TD VALIGN='TOP'>
                <B>Particle Params:</B></A><BR>
                <INPUT TYPE='text' NAME='partdiam' SIZE='5' VALUE='$partdiam'>
                Particle Diameter (in Angstroms)<BR>
                <INPUT TYPE='text' NAME='maskdiam' SIZE='5' VALUE='$maskdiam'>
                Mask Diameter (in Angstroms)<BR>
                <INPUT TYPE='text' NAME='lp' SIZE='5' VALUE='$lp'>
                Low Pass Filter (in Angstroms)<BR>
                </TD>
        </TR>
        <TR>
                <TD VALIGN='TOP'>
                <B>Classification Params:</B></A><BR>
                <INPUT TYPE='text' NAME='numclass' VALUE='$numclass' SIZE='4'>
                Number of Classes to Make<BR>
                <INPUT TYPE='text' NAME='numpart' VALUE='$numpart' SIZE='4'>
                Number of Particles to Use<BR>
                <FONT COLOR=#DD0000>WARNING: more than 3000 particles can takes days to process<BR>
        </TR>\n";
        echo"
                </SELECT>
                </TD>
        </TR>
        </TABLE>
        </TD>
        </TR>
        <TR>
                <TD COLSPAN='2' ALIGN='CENTER'>
                <HR>
                Host: <select name='host'>\n";
        foreach($hosts as $host) {
                $s = ($_POST['host']==$host) ? 'selected' : '';
                echo "<option $s >$host</option>\n";
        }
        echo "</select>
        User: <select name='user'>\n";
        foreach($users as $user) {
                $s = ($_POST['user']==$user) ? 'selected' : '';
                echo "<option $s >$user</option>\n";
        }
	echo"
          </select>
          <BR>
          <input type='submit' name='process' value='Create Stack'><BR>
          <FONT COLOR='RED'>Submission will NOT create a stack, only output a command that you can copy and paste into a unix shell</FONT>
          </TD>
        </TR>
        </TABLE>
        </FORM>
        </CENTER>\n";
	writeBottom();
	exit;
}

function runClassifier() {
        $host = $_POST['host'];
        $user = $_POST['user'];

        $runid=$_POST['runid'];
        $outdir=$_POST['outdir'];
        $stackid=$_POST['stackid'];
        $partdiam=$_POST['partdiam'];
        $maskdiam=$_POST['maskdiam'];
        $lp=$_POST['lp'];

        //make sure a session was selected
        //$description=$_POST['description'];
        //if (!$description) createClassifierForm("<B>ERROR:</B> Enter a brief description of the stack");

        //make sure a session was selected
        //$outdir=$_POST['outdir'];
        //if (!$outdir) createClassifierForm("<B>ERROR:</B> Select an experiment session");

        // make sure outdir ends with '/'
        if (substr($outdir,-1,1)!='/') $outdir.='/';

        // get selexon runId
        //$prtlrunId=$_POST['prtlrunId'];
        //if (!$prtlrunId) createClassifierForm("<B>ERROR:</B> No particle coordinates in the database");
        
        $commit = ($_POST['commit']=="on") ? 'commit' : '';

        // classification
        $numclass=$_POST['numclass'];
        $numpart=$_POST['numpart'];
        if ($numpart > 5000 || $numpart < 10) createClassifierForm("<B>ERROR:</B> Number of particles must be between 10 & 5000");
        if ($numclass > 300 || $numclass < 1) createClassifierForm("<B>ERROR:</B> Number of classes must be between 1 & 300");

        $fileformat = ($_POST['fileformat']=='spider') ? 'spider' : '';

//        $command ="source /ami/sw/ami.csh;";
//        $command.="source /ami/sw/share/python/usepython.csh common32;";
//        $command.="source /home/$user/pyappion/useappion.csh;";
        $command.="classifier.py ";
        $command.="runid=$runid ";
        $command.="outdir=$outdir ";
        $command.="stackid=$stackid ";
        if ($commit) $command.="commit ";
        $command.="numpart=$numpart ";
        $command.="numclass=$numclass ";
        $command.="lp=$lp ";
        if ($partdiam) $command.="diam=$partdiam ";
        if ($maskdiam) $command.="maskdiam=$maskdiam ";
        //if ($fileformat) $command.="spider ";
        //$command.="description=\"$description\"";

        $cmd = "exec ssh $user@$host '$command > classifierlog.txt &'";
//        exec($cmd ,$result);

        writeTop("Classifier Run","Classifier Params");

        echo"
        <P>
        <TABLE WIDTH='600' BORDER='1'>
        <TR><TD COLSPAN='2'>
        <B>Classifier Command:</B><BR>
        $command
        </TD></TR>
        <TR><TD>runid</TD><TD>$runid</TD></TR>
        <TR><TD>stackid</TD><TD>$stackid</TD></TR>
        <TR><TD>numpart</TD><TD>$numpart</TD></TR>
        <TR><TD>numclass</TD><TD>$numclass</TD></TR>
        <TR><TD>partdiam</TD><TD>$partdiam</TD></TR>
        <TR><TD>maskdiam</TD><TD>$maskdiam</TD></TR>
        <TR><TD>outdir</TD><TD>$outdir</TD></TR>
        <TR><TD>lowpass</TD><TD>$lp</TD></TR>
        </TABLE>\n";
        //<TR><TD>description</TD><TD>$description</TD></TR>
        //<TR><TD>commit</TD><TD>$commit</TD></TR>
        //<TR><TD>fileformat</TD><TD>$fileformat</TD></TR>
        writeBottom();
}
?>
