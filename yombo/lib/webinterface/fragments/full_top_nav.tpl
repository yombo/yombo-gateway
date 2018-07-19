        <nav class="navbar navbar-default navbar-fixed-top" role="navigation" style="margin-bottom: 0">
            <div class="navbar-header">
                <button type="button" class="navbar-toggle" data-toggle="collapse" data-target=".navbar-collapse">
                    <span class="sr-only">Toggle navigation</span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                </button>
                <div class="menu-toggler sidebar-toggler">
                    <span class="sr-only">Toggle navigation</span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                    <span class="icon-bar"></span>
                </div>
                <a class="navbar-brand" href="/?">{{ misc_wi_data.gateway_label() }}</a>

	            <ul class="nav navbar-top-links navbar-right">
	                <!-- /.dropdown -->
	                <li class="dropdown">
	                    <a class="dropdown-toggle" data-toggle="dropdown" href="#">
						<span class="fa-stack fa-1x has-badge" data-count="{{misc_wi_data.notifications.get_unreadbadge_count()}}">
						  <i class="fa fa-bell fa-stack-1x"></i>
						</span>&nbsp;
						<i class="fa fa-caret-down"></i>
	                    </a>
	                    <ul class="dropdown-menu dropdown-alerts">
						{% if misc_wi_data.notifications|length > 0 %}
							{% for id, notice in misc_wi_data.notifications.notifications[:6].items() %}
								<li>
									<a href="/notifications/{{ id }}/details">
										<div>
											{% if notice.priority == 'bug' %}
											<i class="fa fa-bug fa-fw" style="color:black;"></i>
											{% elif notice.priority == 'low' %}
											<i class="fa fa-arrow-down fa-fw" style="color:rgba(0,115,225,0.7);"></i>
											{% elif notice.priority == 'normal' %}
											<i class="fa fa-info fa-fw" style="color:rgba(0,115,225,0.7);"></i>
											{% elif notice.priority == 'high' %}
											<i class="fa fa-arrow-up fa-fw" style="color:rgba(239,231,50,0.8);"></i>
											{% elif notice.priority == 'urgent' %}
											<i class="fa fa-exclamation-triangle fa-fw" style="color:rgba(185,12,24,0.81);"></i>
											{% endif %}
											{{ notice.title }}
											<span class="pull-right text-muted small">{{ notice.created|epoch_to_pretty_date }}</span>
										</div>
									</a>
								</li>
								<li class="divider"></li>
							{% endfor %}
	                        <li>
	                            <div style="text-align:center">
									<a class="text-center" href="/notifications/index">
	                                <strong>See All ({{ misc_wi_data.notifications.__len__() }})</strong>
	                                <i class="fa fa-angle-right"></i>
	                            </a>
								</div>
	                        </li>
						{% else %}
							<div style="text-align:center"><strong> No notifications</strong></div>
						{% endif %}
	                    </ul>
	                    <!-- /.dropdown-alerts -->
	                </li>
	                <!-- /.dropdown -->
	                <li class="dropdown">
	                    <a class="dropdown-toggle" data-toggle="dropdown" href="#">
	                        <i class="fa fa-user fa-fw"></i>  <i class="fa fa-caret-down"></i>
	                    </a>
	                    <ul class="dropdown-menu dropdown-user">
	                        <li><a href="https://yg2.in/f_gw_my_account"><i class="fa fa-user fa-fw"></i>&nbsp;User Profile</a>
	                        </li>
	                        <li><a href="https://yg2.in/f_gw_docs"><i class="fa fa-book fa-fw"></i>&nbsp;Documentation</a>
	                        </li>
	                        <li><a href="https://yg2.in/f_gw_yombonet"><i class="fa fa-globe fa-fw"></i>&nbsp;Yombo.Net</a>
	                        </li>
	                        <li class="divider"></li>
	                        <li><a class="confirm-logout" href="#"><i class="fa fa-sign-out-alt fa-fw"></i>&nbsp;Logout</a>
	                        </li>
	                        <li class="divider"></li>
	                        <li><a class="confirm-restart" href="#"><i class="fa fa-recycle fa-fw"></i>&nbsp;Restart</a>
	                        </li>
	                        <li><a class="confirm-shutdown" href="#"><i class="fa fa-power-off fa-fw"></i>&nbsp;Shutdown</a>
	                        </li>
	                    </ul>
	                    <!-- /.dropdown-user -->
	                </li>
	                <!-- /.dropdown -->
	            </ul>
	            <!-- /.navbar-top-links -->
			</div>
            <!-- /.navbar-header -->
        </nav>

