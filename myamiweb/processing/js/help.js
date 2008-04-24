/**
 * help key : value defined in javascript object notation
 */

var help = {
/**	'appion' : {
*	}
**/
	'eman' : {
		'runid' : 'Specifies the name associated with the processing results unique to the specified session and parameters. An attempt to use the same run name for a session using different processing parameters will result in an error.',
		'checkimages' : 'Choose what images to process here.  Images can be inspected by Viewer or ImageAssessor.  BEST images include ones inspected as KEEP or as EXEMPLAR in the viewer.  NON-REJECTED images include the BEST images above-mentioned and the uninspected ones and therefore exclude only the REJECTED or HIDDEN images.',
		'nowait' : 'By default the program will check to see if Leginon has collected more images after finishing for 2 hours. If this is unchecked then when the program finishes it will immediately stop.',
		'background' : 'This a feature the turns off some of the fancy output used when the program runs',
		'shuffle' : 'The shuffle feature shuffles the order of the images before the processing begins that way you do not always start from the beginning.',
		'limit' : 'If you do not want to process all the images, enter a number and the program will only process this number of images. Good for testing a few images before committing the results to the database.',
		'cont' : 'By default you ALWAYS want to continue, unless you are NOT committing to the database yet and you want to reprocess an image.',
		'commit' : 'This is the main checkbox of the program. When testing do NOT commit, but once you are happy with the results. Start commiting the data otherwise all information will be lost.',
		'minthresh' : 'Threshold for particle picking from the cross-correlation or dogpicker map. Any values above this threshold are considered particles.<br/>Fortemplate correlation, this should be between 0.0 and 1.0, typically 0.4 to 0.6 is used.<br/>For dogPicker, the values is in terms of standard deviations from the mean divided by four. Reasonable range from 0.4 to 3.0 with typical values falling between 0.7 and 1.0',
		'maxthresh' : 'Maximum threshold for particle picking from the cross-correlation or dogpicker map. Any values above this threshold are rejected.<br/>For template correlation, you probably do not need this, but typical values would be between 0.7 and 0.8.<br/>For dogPicker, the values is in terms of standard deviations from the mean divided by four. Reasonable range from 1.0 to 5.0 with typical values falling between 1.5 and 2.5',
		'maxpeaks' : 'This a feature limits the number of particles allowed in an image. By default it is set to 1500, but if you want no more than 50 particles an image fill in this value',
		'lpval' : 'Low pass filtering of the image before picking. This should be about 1/10 to 1/50 of the particle diameter, <I>e.g.</I> for a particle with diameter 150 &Aring;, a low pass of 5-10 &Aring; works pretty good',
		'hpval' : 'High pass filtering of the image before picking. This removes any darkness gradients in the image. Typically you could disable this by setting it equal to zero, otherwise 600 work pretty good. Warning this feature typically normalizes the crud so more particles get picked from crud.',
		'medianval' : 'Median filtering of the image before picking. This helps remove any noise spikes in the image. Typical values are 2, 3, or 5. The bigger the number the more information is thrown away.',
		'binval' : 'Binning of the image. This takes a power of 2 (1,2,4,8,16) and shrinks the image to help make the processing faster. Typically you want to use 4 or 8 depending on the quality of you templates.',
		'defocpair' : 'If defocal pairs were collected you want to use this. This feature takes both of the en and ef images and aligns them, so you can use makestack later.',
		'maxsize' : 'Max size multiple of the particle peak. When the peak is found in the thresholded image it has a size in pixels. Now if that size is greater than maxsize*particle diameter then the peak is rejected.',
		'overlapmult' : 'The overlap multiple specifies the minimum distance allowed between two peaks. If two peaks are closer than overlapmult*particle diameter the only the larger of the two peaks is retained.',
		'pixlimit' : 'Limit the values of the pixels to within this number of standard deviations from the mean. 0.0 turns this feature off.',
		'kfactor' : 'The k-factor for dogpicker defines the slopiness in diameter of the picked particles. A k-factor of 1.00001 gives only the exact diameter (1.0 is not allowed), but a k-factor of 5.0 will pick a wide range of sizes. Cannot be used with multi-scale dogpicker: numslices or sizerange',
		'numslices' : 'Defines the number of different sizes (or slices) to break up the size range into for separating particles of different size.',
		'sizerange' : 'Defines the range of sizes for separating particles of different size.',
		'invert' : 'Sometimes the template is inverted to the images or dogPicker needs inverted images in this case use the invert flag.',
		'nojpegs' : 'Do NOT write out the summary jpegs for image assessor.',

/**
* these should be separate
**/
		'imask' : 'Radius of internal mask (in pixels)',
		'nodes' : 'Nodes refers to the number of computer to process on simultaneously. The more nodes you get the faster things will get process, but more nodes requires that you wait longer before being allowed to begin processing.',
		'walltime' : 'Wall time, also called real-world time or wall-clock time, refers to elapsed time as determined by a chronometer such as a wristwatch or wall clock. (The reference to a wall clock is how the term originally got its name.)',
		'cputime' : 'Wall time, also called real-world time or wall-clock time, refers to elapsed time as determined by a chronometer such as a wristwatch or wall clock. (The reference to a wall clock is how the term originally got its name.)',
		'procpernode' : 'Processors per node. Each computer (node) or Garibaldi has 4 processors (procs), so proc/node=4. For some cases, you may want to use less processors on each node, leaving more memory and system resources for each process.',
		'ang' : 'Angular step for projections (in degrees)',
		'itn' : 'Iteration Number',
		'copy' : 'Duplicate the parameters for this iteration',
		'mask' : 'Radius of external mask (in pixels)',
		'imask' : 'Radius of internal mask (in pixels)',
		'amask' : '<b>amask=[r],[threshold],[iter]</b><br />Must be used in conjunction with xfiles - This option applies an automatically generated \'form fitting\' soft mask to the model after each iteration.  The mask generation is generally quite good.  It uses 3 values :<br />First - the smallest radius from the center of the map that contacts some density of the \'good\' part of the map.<br />Second - A threshold density at which all of the undesirable density is disconnected from the desired mass.<br />Third - A number of 1-voxel \'shells\' to include after the correct density has been located (this allows you to use threshold densities higher than the desired isosurface threshold density). The iterative shells will include a \'soft\' Gaussian edge after 2 pixels. ie - if you add 8 shells, the density will decay in this region using a 1/2 width of 3 pixels starting at the 3rd pixel. If the number of shells is specified as a negative value, then the mask will have a sharp edge, and any hollow areas inside the mask will be filled in.',
		'sym' : 'Imposes symmetry on the model, omit this option for no/unknown symmetry<BR/>Examples: c1, c2, d7, etc.',
		'hard' : 'Hard limit for <I>make3d</I> program. This specifies how well the class averages must match the model to be included, 25 is typical',
		'clskeep' : '<b>classkeep=[std dev multiplier]</b><br />This determines how many raw particles are discarded for each class-average. This is defined in terms of the standard-deviation of the self-similarity of the particle set. A value close to 0 (should not be exactly 0) will discard about 50% of the data. 1 is a typical value, and will typically discard 10-20% of the data.',
		'clsiter' : 'Generation of class averages is an iterative process. Rather than just aligning the raw particles to a reference, they are iteratively aligned toeach other to produce a class-average representative of the data, not of the model, eliminating initial model bias. Typically set to 8 in the early rounds and 3 in later rounds - 0 may be used at the end, but model bias may result.',
		'filt3d' : '<b>fil3d=[rad]</b><br />Applies a gaussian low-pass filter to the 3D model between iterations. This can be used to correct problems that may result in high resolution terms being upweighted. [rad] is in pixels, not Angstroms',
		'shrink' : '<b>shrink=[n]</b><br /><i>Experimental</i>, Another option that can produce dramatic speed improvements. In some cases, this option can actually produce an improvement in classification accuracy. This option scales the particles and references down by a factor of [n] before classification. Since data is often heavily oversampled, and classification is dominated by low resolution terms, this can be both safe, and actually improve classification by \'filtering\' out high resolution noise. Generally shrink=2 is safe and effective especially for early refinement. In cases of extreme oversampling, larger values may be ok. This option should NOT be used for the final rounds of refinement at high resolution.',
		'euler2' : '<b>euler2=[oversample factor]</b><br /><i>Experimental</i>, This option should improve convergence and reconstruction quality, but has produced mixed results in the past. It adds an additional step to the refinement process in which class-averages orientations are redetermined by projection-matching. The parameter allows you to decrease the angular step (ang=) used to generateprojections. ie - 2 would produce projections with angular step of ang/2. It may be worth trying, but use it with caution on new projects.',
		'perturb' : '<i>Experimental</i>, potentially useful and at worst should be harmless. Has not been well characterized yet. Rather than generating Euler angles at evenly spaced positions, it adds some randomness to the positions. This should produce a more uniform distribution of data in 3D Fourier space and reduce Fourier artifacts',
		'xfiles' : '<b>xfiles=[mass in kD]</b><br />A convenience option.  For each 3D model it will produce a corresponding x-file (threed.1a.mrc -> x.1.mrc).  Based on the mass, the x-file will be scaled so an isosurface threshold of 1 will contain the specified mass.',
		'tree' : 'This can be a risky option, but it can produce dramatic speedups in the refinement process. Rather than comparing each particle to every reference, this will decimate the reference population to 1/4 (if 2 is specified) or 1/9 (if 3 is specified) of its original size, classify, then locally determine which of the matches is best. Is is safest in conjunction with very small angular steps, ie - large numbers of projections. The safest way to use this is either:<br /><i>a)</i> for high-resolution, small-ang refinement or <br/><i>b)</i> for the initial iterations of refinement (then turn it off for the last couple of iterations).',
		'median' : 'When creating class averages, use the median value for each pixel instead of the average.  Not recommended for larger datasets, as it can result in artifacts.  If your dataset is noisy, and has small particles this is recommended',
		'phscls' : 'This option will use signal to noise ratio weighted phase residual as a classification criteria (instead of the default optimized real space variance). Over the last year or so, people working on cylindrical structures (like GroEL), have noticed that \'side views\' of this particle seem to frequently get classified as being tilted 4 or 5 degrees from the side view. While apparently this didn\'t effect the models significantly at the obtained resolution, it is quite irritating. This problem turns out to be due to resolution mismatch between the 3D model and the individual particles. Using phase residual solves this problem, although it\'s unclear if there is any resolution improvement. This option has a slight speed penalty',
		'fscls' : 'An improvement, albeit an experimental one, over phasecls. phasecls ignores Fourier amplitude when making image comparisons. fscls will use a SNR weighted Fourier shell correlation as a similarity criteria. Preliminary tests have shown that this produces slightly better results than phasecls, but it should still be used with caution.',
		'refine' : 'This will do subpixel alignment of the particle translations for classification and averaging. May have a significant impact at higher resolutions (with a speed penalty).',
		'goodbad' : 'Saves good and bad class averages from 3D reconstruction. Overwrites each new iteration.',
		'eotest' : 'Run the <I>eotest</I> program that performs a 2 way even-odd test to determine the resolution of a reconstruction.',
		'coran' : 'Use correspondence analysis particle clustering algorithm'
	}
}
