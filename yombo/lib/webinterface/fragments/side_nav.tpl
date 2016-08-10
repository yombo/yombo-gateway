
        <nav role="navigation" style="margin-bottom: 0; margin-top: -1px;">
            <div class="navbar-default sidebar" role="navigation">
                <div class="sidebar-nav navbar-collapse" id="sidebar-area">
                    <ul class="nav" id="sidebar">
                        <li class="sidebar-search">
                            <div class="input-group custom-search-form">
                                <input type="text" class="form-control" placeholder="Search...">
                                <span class="input-group-btn">
                                <button class="btn btn-default" type="button">
                                    <i class="fa fa-search"></i>
                                </button>
                            </span>
                            </div>
                            <div  class="search-icon">
                            	<a href="#"><i class="fa fa fa-search fa-fw"></i></a>
                            </div>
                            <!-- /input-group -->
                        </li>
                        <li>
                            <a href="/"><i class="fa fa-home fa-fw"></i> <span class="side-menu-title">Home</span></a>
                        </li>
        {%- for priority1, items in data.nav_side.iteritems() -%}
            {% set printed_nested_header = False -%}
            {% for item in items -%}
                {% if items|length > 1 -%}
                {% endif -%}
                {% if items|length > 1 -%}
                    {% if printed_nested_header == False -%}
                        {% set printed_nested_header = True %}
						<li>
                            <a href="#" class="dropdown-collapse"><i class="{{ item.icon }}"></i> <span class="side-menu-title">{{ item.label1 }}</span><span class="fa arrow"></span></a>
                            <ul class="nav nav-second-level">
                    {%- endif %}
                                <li>
                                    <a href="{{ item.url }}">{{ item.label2 }}</a>
                                </li>
                {%- else %}
                        <li><a href="{{ item.url }}"><i class="{{ item.icon }}"></i> <span class="side-menu-title">{{ item.label1 }}</span></a></li>
                {%- endif -%}
            {% endfor -%}
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
