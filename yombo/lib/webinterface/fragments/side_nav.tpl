        <nav role="navigation" style="margin-bottom: 0; margin-top: -1px;">
            <div class="navbar-default sidebar" role="navigation">
                <div class="sidebar-nav navbar-collapse" id="sidebar-area">
                    <ul class="nav" id="sidebar">
                        <!--<li class="sidebar-search">-->
                            <!--<div class="input-group custom-search-form">-->
                                <!--<input type="text" class="form-control" placeholder="Search...">-->
                                <!--<span class="input-group-btn">-->
                                <!--<button class="btn btn-default" type="button">-->
                                    <!--<i class="fa fa-search"></i>-->
                                <!--</button>-->
                            <!--</span>-->
                            <!--</div>-->
                            <!--<div  class="search-icon">-->
                            	<!--<a href="#"><i class="fa fa fa-search fa-fw"></i></a>-->
                            <!--</div>-->
                            <!--&lt;!&ndash; /input-group &ndash;&gt;-->
                        <!--</li>-->
                        <li>
                            <a href="/?"><i class="fa fa-home fa-fw"></i> <span class="side-menu-title">Home</span></a>
                        </li>
        {%- for priority1, items in misc_wi_data.nav_side.items() -%}
            {% set printed_nested_header = False -%}
            {% if items|length > 1 %}
						<li>
                            <a href="#" class="dropdown-collapse"><i class="{{ items[0].icon }}"></i> <span class="side-menu-title">{{ _(items[0].label1, items[0].label1_text) }}</span><span class="fa fa-arrow-down pull-right"></span></a>
                            <ul class="nav nav-second-level">
                {% for item in items -%}
                                    <li>
                                        <a href="{{ item.url }}">{{ _(item.label2, item.label2_text) }}</a>
                                    </li>
                {% endfor -%}

            {%- else %}
                        <li><a href="{{ items[0].url }}"><i class="{{ items[0].icon }}"></i> <span class="side-menu-title">{{ _(items[0].label1, items[0].label1_text) }}</span></a></li>
            {%- endif -%}
            {% if items|length > 1 %}
                            </ul>
                            <!-- /.nav-second-level -->
                        </li>
            {%- endif -%}
        {%- endfor %}
                    </ul>
                </div>
                <!-- /.sidebar-collapse -->
            </div>
            <!-- /.navbar-static-side -->
        </nav>
